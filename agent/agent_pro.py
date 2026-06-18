import os
import sys
import subprocess
import time
import re
import json
import yaml
import signal
import threading
from io import StringIO
import requests as req
import urllib3
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from agent.orchestrator import OrchestratorAgent
from utils.prompt_manager import PromptManager
import gradio as gr

from agent.model_backend import ModelBackend, LlamaCppBackend
from agent.knowledge_base import C64KnowledgeBase

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PREDEFINED = [
    ("6502org", "6502.org"),
    ("codebase64", "Codebase64"),
    ("c64wiki", "C64-Wiki"),
    ("thefridge", "The Fridge"),
    ("lemon64", "Lemon64"),
    ("project64", "Project 64"),
    ("nesdev", "NESdev 6502"),
]
CUSTOM_SITES_FILE = "data/custom_sites.json"


class ProcessControl:
    def __init__(self):
        self.reset()

    def reset(self):
        self.proc = None
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.cancelled = False
        self.running = False
        self.start_time = None
        self.current_step = ""

    def pause(self):
        self.pause_event.clear()
        if self.proc and self.proc.poll() is None and hasattr(signal, "SIGSTOP"):
            self.proc.send_signal(signal.SIGSTOP)

    def resume(self):
        self.pause_event.set()
        if self.proc and self.proc.poll() is None and hasattr(signal, "SIGCONT"):
            try:
                self.proc.send_signal(signal.SIGCONT)
            except ProcessLookupError:
                pass

    def cancel(self):
        self.cancelled = True
        self.pause_event.set()
        if self.proc and self.proc.poll() is None:
            self.proc.kill()

    def check_pause(self):
        while not self.pause_event.is_set() and not self.cancelled:
            time.sleep(0.5)

    def elapsed(self):
        if self.start_time:
            t = int(time.time() - self.start_time)
            m, s = divmod(t, 60)
            return f"{m:02d}:{s:02d}"
        return "00:00"


CTRL = ProcessControl()
agent = None


def load_custom_sites():
    if os.path.exists(CUSTOM_SITES_FILE):
        with open(CUSTOM_SITES_FILE) as f:
            return json.load(f)
    return []


def save_custom_site(name, url):
    sites = load_custom_sites()
    if any(s["url"] == url for s in sites):
        return
    sites.append({"name": name, "url": url})
    os.makedirs(os.path.dirname(CUSTOM_SITES_FILE), exist_ok=True)
    with open(CUSTOM_SITES_FILE, "w") as f:
        json.dump(sites, f, indent=2)


def remove_custom_site(name):
    sites = load_custom_sites()
    sites = [s for s in sites if s["name"] != name]
    with open(CUSTOM_SITES_FILE, "w") as f:
        json.dump(sites, f, indent=2)


def all_site_choices():
    choices = [(label, key) for key, label in PREDEFINED]
    for s in load_custom_sites():
        choices.append((s["name"], s["name"]))
    return choices


def _extract_urls(text: str) -> list[str]:
    urls = re.findall(r'https?://[^\s<>"\')\]}\[|，、，]+', text)
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        u = u.rstrip(".,:;!?)'\"")
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def _domain_name(url: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    name = re.sub(r"^www\.", "", parsed.netloc or parsed.path)
    return name[:50]


class C64CodingAgent:
    def __init__(
        self,
        base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        lora_path=None,
        gguf_path=None,
    ):
        if gguf_path and os.path.exists(gguf_path):
            print(f"Loading GGUF model for CPU: {gguf_path}")
            self.backend = LlamaCppBackend(gguf_path)
            self.tokenizer = None
        else:
            try:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                )

                print(f"Loading base model: {base_model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    base_model_name, trust_remote_code=True
                )
                model = AutoModelForCausalLM.from_pretrained(
                    base_model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True,
                )

                base_model = model
                if lora_path and os.path.exists(lora_path):
                    print(f"Loading LoRA from: {lora_path}")
                    model = PeftModel.from_pretrained(model, lora_path)

                self.backend = ModelBackend(
                    model, self.tokenizer, base_model=base_model
                )
            except Exception as e:
                print(f"Error loading model with transformers: {e}")
                print(
                    "Falling back to CPU-only mode (Mock/GGUF placeholder if path missing)"
                )
                self.backend = LlamaCppBackend(gguf_path)
                self.tokenizer = None

        self.pm = PromptManager()
        self.orchestrator = OrchestratorAgent(self.backend, self.tokenizer, pm=self.pm)
        self._current_lora = None

    def set_lora(self, lora_path):
        if not lora_path or not os.path.exists(lora_path):
            return False
        ok = self.backend.load_lora(lora_path)
        if ok:
            self._current_lora = lora_path
        return ok

    def unload_lora(self):
        self.backend.unload_lora()
        self._current_lora = None
        return True

    @property
    def active_lora(self):
        return self._current_lora

    def chat_wrapper(self, message, history, mode, auto_scrape):
        use_rag = mode in ("RAG", "RAG+LoRA")
        formatted_history: list[tuple[str, str]] = []
        for item in history:
            if isinstance(item, dict):
                formatted_history.append((item.get("content", ""), ""))
            elif len(item) >= 2:
                formatted_history.append((str(item[0]), str(item[1])))
            else:
                formatted_history.append((str(item), ""))

        try:
            max_attempts = int(self.pm.get_config("agent.max_attempts", 3))
            response, sources, logs = self.orchestrator.process_request(
                message,
                use_rag=use_rag,
                chat_history=formatted_history,
                max_attempts=max_attempts,
            )

            base = response
            yield base

            if not auto_scrape:
                return

            all_urls = _extract_urls(message) + _extract_urls(response)
            all_urls = list(dict.fromkeys(all_urls))
            if not all_urls:
                return

            yield base + "\n\n---\n🔍 **Link trovati, avvio elaborazione...**"

            added = 0
            existing = {s["url"] for s in load_custom_sites()}
            for url in all_urls:
                if url not in existing:
                    save_custom_site(_domain_name(url), url)
                    existing.add(url)
                    added += 1

            if added:
                yield (
                    base
                    + f"\n\n---\n📌 **{added} nuovi siti aggiunti.** Avvio pipeline..."
                )
            else:
                yield base + "\n\n---\n📌 **Siti già presenti.** Avvio pipeline..."

            for idx, url in enumerate(all_urls, 1):
                yield (
                    base
                    + f"\n\n---\n🔄 **[{idx}/{len(all_urls)}]** {_domain_name(url)}"
                )
                last, count = "", 0
                for msg in download_and_integrate(url):
                    last, count = msg, count + 1
                    if count % 5 == 0:
                        yield base + f"\n\n---\n🔄 **{_domain_name(url)}**\n{last}"
                yield (
                    base
                    + f"\n\n---\n✅ **[{idx}/{len(all_urls)}]** {_domain_name(url)}\n{last}"
                )

            yield (
                base
                + f"\n\n---\n✅ **Pipeline completata per {len(all_urls)} URL — KB aggiornata!**"
            )

        except Exception as e:
            yield f"Errore durante l'elaborazione: {str(e)}"


def get_hints(message):
    if not message:
        return ""
    m = message.lower()
    hints = []

    if any(kw in m for kw in ["bordo", "border", "$d020", "d020", "colore bordo", "colore dello sfondo", "$d021", "d021", "53280", "53281", "colore", "color"]):
        hints.append("""**🎨 Colori C64 (0-15)**
0=Nero 1=Bianco 2=Rosso 3=Ciano
4=Viola 5=Verde 6=Blu 7=Giallo
8=Arancione 9=Marrone 10=Rosa 11=Grigio scuro
12=Grigio medio 13=Verde chiaro 14=Azzurro 15=Grigio chiaro
`$D020`(53280)=bordo `$D021`(53281)=sfondo""")

    if any(kw in m for kw in ["sprite", "sprite 0", "sprite 1"]):
        hints.append("""**🟦 Registri Sprite VIC-II**
$D015 = enable, $D000-$D00F = X/Y (8 sprite),
$D010 = MSB X, $D027-$D02E = colore,
$D017 = expand Y, $D01D = expand X,
$D01C = multicolor, $07F8-$07FF = pointer""")

    if any(kw in m for kw in ["raster", "raster interrupt", "irq", "$d012", "d012"]):
        hints.append("""**⚡ Raster Interrupt**
$D012 = linea raster confronto, $D01A = IRQ mask (bit 0),
$0314/$0315 = vettore IRQ (ROM), $FFFE/$FFFF = vettore NMI
`SEI` / `CLI` = disabilita/abilita interrupt""")

    if any(kw in m for kw in ["sid", "musica", "suono", "audio", "$d400", "d400", "psid"]):
        hints.append("""**🔊 SID 6581 ( $D400-$D418 )**
$D400-$D401 = freq voice 1, $D402-$D403 = pulse width,
$D404 = controllo (gate/test/ring/sync/rect/saw/tri/noise),
$D405-$D406 = ADSR, $D40B-$D40C = freq voice 2,
$D412-$D413 = ADSR voice 2, $D415 = filtro cutoff low,
$D418 = volume + filtro""")

    if any(kw in m for kw in ["joystick", "joy", "cia", "$dc00", "dc00", "$dc01", "dc01"]):
        hints.append("""**🎮 CIA 1 — Joystick & Keyboard**
$DC00 = porta A (joystick 1 / colonne tastiera),
$DC01 = porta B (joystick 2 / righe tastiera)
Bits: 0=up, 1=down, 2=left, 3=right, 4=fire""")

    if any(kw in m for kw in ["kernal", "kernal routine", "$ffe0", "chrout", "ffd2", "$ffd2"]):
        hints.append("""**💾 KERNAL Routines principali**
$FFD2 = CHROUT (scrive un carattere), $FFE4 = GETIN (legge tastiera),
$FFCF = PLOT (get/set cursore), $FF81 = screen editor init,
$FF5B = SETLFS, $FFBD = SETNAM, $FFD5 = LOAD, $FFD8 = SAVE""")

    return "\n\n".join(hints)


def log_msg(msg):
    return f"[{CTRL.elapsed()}] {msg}"


def run_cmd_gen(cmd, env=None):
    yield log_msg(f"Avvio: {cmd}")
    CTRL.check_pause()
    if CTRL.cancelled:
        yield log_msg("ANNULLATO")
        return
    try:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        popen_kwargs = dict(
            args=cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=merged_env,
        )
        # Windows non supporta preexec_fn
        if hasattr(os, "setsid"):
            popen_kwargs["preexec_fn"] = os.setsid
        CTRL.proc = subprocess.Popen(**popen_kwargs)
        lines = []
        errored = False
        for line in iter(CTRL.proc.stdout.readline, ""):
            CTRL.check_pause()
            if CTRL.cancelled:
                CTRL.proc.kill()
                yield log_msg("ANNULLATO")
                return
            lines.append(line.rstrip())
            # Check if the line contains error indicators
            if any(
                kw in line.lower()
                for kw in ["error", "traceback", "exception", "errore"]
            ):
                errored = True
            yield "\n".join(lines[-80:])
        CTRL.proc.wait()
        rc = CTRL.proc.returncode
        if rc != 0 or errored:
            lines.append(
                log_msg(
                    f"ERRORE: codice {rc}"
                    + (f" (rilevato errore nel log)" if rc == 0 else "")
                )
            )
            yield "\n".join(lines[-80:])
        else:
            lines.append(log_msg("OK"))
            yield "\n".join(lines[-80:])
    except Exception as e:
        yield log_msg(f"ERRORE: {e}")
    finally:
        CTRL.proc = None


def _extract_html_text(html_path, out_path):
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._text = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                self._text.append(data)

    parser = TextExtractor()
    with open(html_path, "r", errors="replace") as f:
        parser.feed(f.read())
    text = "\n".join(parser._text)
    with open(out_path, "w") as f:
        f.write(text)


def _extract_epub_text(epub_path, out_path):
    import zipfile
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self._text = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                self._text.append(data)

    all_text = []
    with zipfile.ZipFile(epub_path) as z:
        for name in z.namelist():
            if name.endswith((".xhtml", ".html", ".htm")):
                parser = TextExtractor()
                parser.feed(z.read(name).decode("utf-8", errors="replace"))
                all_text.extend(parser._text)
    with open(out_path, "w") as f:
        f.write("\n".join(all_text))


def download_and_integrate(url):
    if not url or CTRL.cancelled:
        return
    url = url.strip()
    CTRL.start_time = time.time()
    CTRL.running = True

    is_pdf = url.lower().endswith(".pdf")
    is_d64 = url.lower().endswith(".d64")
    is_prg = url.lower().endswith(".prg")
    is_g64 = url.lower().endswith(".g64")
    is_archive = "archive.org" in url
    is_gdrive = "drive.google.com" in url

    if is_gdrive:
        dest_dir = "data/input"
        os.makedirs(dest_dir, exist_ok=True)
        match = re.search(r"/drive/folders/([^/?]+)", url)
        if not match:
            yield log_msg("URL Google Drive non valido.")
            return
        folder_id = match.group(1)
        out_dir = os.path.join(dest_dir, "drive_" + folder_id)
        os.makedirs(out_dir, exist_ok=True)
        yield log_msg("━━━ Google Drive ━━━")
        yield log_msg(f"  ID cartella: {folder_id}")
        yield log_msg(f"  Destinazione: {out_dir}")
        yield log_msg("  Installazione gdown...")
        yield from run_cmd_gen("pip install -q gdown")

        yield log_msg("  Enumerazione file nella cartella...")
        import gdown as _gd

        files_info = _gd.download_folder(
            id=folder_id, output=out_dir, quiet=True, skip_download=True
        )
        if not files_info:
            yield log_msg(
                "  ⚠ Nessun file trovato. Verifica che la cartella sia pubblica."
            )
        else:
            dirs_map: dict[str, list] = {}
            for f in files_info:
                p = os.path.dirname(f.local_path)
                dirs_map.setdefault(p, []).append(f)
            yield log_msg(
                f"  Trovati {len(files_info)} file in {len(dirs_map)} sottocartelle:"
            )
            for d, flist in sorted(dirs_map.items()):
                rel = os.path.relpath(d, out_dir)
                if rel == ".":
                    rel = "(radice)"
                yield log_msg(f"    [{len(flist):2d}] {rel}")
            yield log_msg(
                "  Download in corso... (file grandi potrebbero richiedere tempo)"
            )
            ok = 0
            err = 0
            skip = 0
            for i, f in enumerate(files_info, 1):
                os.makedirs(os.path.dirname(f.local_path), exist_ok=True)
                fname = os.path.basename(f.local_path)
                if os.path.exists(f.local_path):
                    sz = os.path.getsize(f.local_path)
                    yield log_msg(
                        f"  [{i:3d}/{len(files_info)}] {fname}  — {sz / 1024 / 1024:.1f} MB (già presente)"
                    )
                    skip += 1
                    continue
                yield log_msg(f"  [{i:3d}/{len(files_info)}] {fname}  — download...")
                downloaded = False
                try:
                    result = _gd.download(id=f.id, output=f.local_path, quiet=True)
                    if result:
                        downloaded = True
                except Exception:
                    pass
                if not downloaded:
                    try:
                        direct_url = f"https://drive.google.com/uc?id={f.id}&export=download&confirm=t"
                        r = req.get(
                            direct_url, stream=True, timeout=120, allow_redirects=True
                        )
                        if r.status_code == 200 and "text/html" not in r.headers.get(
                            "content-type", ""
                        ):
                            with open(f.local_path, "wb") as fout:
                                for chunk in r.iter_content(8192):
                                    fout.write(chunk)
                            downloaded = True
                    except Exception:
                        pass
                if downloaded:
                    sz = os.path.getsize(f.local_path)
                    yield log_msg(
                        f"  [{i:3d}/{len(files_info)}] {fname}  — {sz / 1024 / 1024:.1f} MB ✓"
                    )
                    ok += 1
                else:
                    yield log_msg(
                        f"  [{i:3d}/{len(files_info)}] {fname}  — ERRORE download ✗"
                    )
                    err += 1
                if i < len(files_info):
                    time.sleep(1.5)
            yield log_msg(
                f"  ══ Riepilogo: {ok} scaricati, {skip} già presenti, {err} errori ══"
            )

    if is_pdf or is_d64 or is_prg or is_g64 or is_archive or is_gdrive:
        dest = "data/input"
        os.makedirs(dest, exist_ok=True)

        if is_archive:
            yield log_msg("Analizzo contenuto Archive.org...")
            from agent.crawler import WebCrawlerAgent
            import json as _json

            match = re.search(r"details/([^/?]+)", url)
            if not match:
                yield log_msg("URL Archive.org non valido.")
                return
            item_id = match.group(1)

            resp = req.get(f"https://archive.org/metadata/{item_id}", timeout=15)
            resp.raise_for_status()
            meta = resp.json()
            files = meta.get("files", [])

            d64_files = [f for f in files if f["name"].lower().endswith(".d64")]
            g64_files = [f for f in files if f["name"].lower().endswith(".g64")]
            prg_files = [f for f in files if f["name"].lower().endswith(".prg")]

            disk_files = d64_files + g64_files + prg_files

            FORMAT_PRIORITY = [
                (".txt", "txt"),
                (".epub", "epub"),
                (".html", "html"),
                (".htm", "html"),
                (".pdf", "pdf"),
            ]

            def pick_best(files_list):
                best = None
                best_idx = len(FORMAT_PRIORITY)
                for f in files_list:
                    ext = os.path.splitext(f["name"].lower())[1]
                    for idx, (fmtext, _) in enumerate(FORMAT_PRIORITY):
                        if ext == fmtext:
                            if idx < best_idx:
                                best = f
                                best_idx = idx
                            break
                return best

            text_file = pick_best(files)

            if disk_files:
                yield log_msg(f"Trovati {len(disk_files)} file disco/PRG. Download...")
                subdir = os.path.join(dest, item_id)
                os.makedirs(subdir, exist_ok=True)
                for df in disk_files:
                    fname = df["name"]
                    dl_url = f"https://archive.org/download/{item_id}/{fname}"
                    yield log_msg(f"  Download: {fname}")
                    try:
                        r = req.get(dl_url, stream=True, timeout=60, verify=False)
                        r.raise_for_status()
                    except Exception as e:
                        yield log_msg(f"  ERRORE download {fname}: {e}")
                        continue
                    local = os.path.join(subdir, os.path.basename(fname))
                    with open(local, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    ext = os.path.splitext(fname)[1].lower()
                    if ext == ".d64":
                        yield from run_cmd_gen(
                            f'python pipeline/extract_d64.py "{local}" "{subdir}"'
                        )
                    elif ext == ".g64":
                        yield from run_cmd_gen(
                            f'python pipeline/extract_g64.py "{local}" "{subdir}"'
                        )
                    elif ext == ".prg":
                        yield from run_cmd_gen(
                            f'python pipeline/extract_prg.py "{local}" "{subdir}"'
                        )

            if text_file:
                fname = text_file["name"]
                ext = os.path.splitext(fname.lower())[1]
                dl_url = f"https://archive.org/download/{item_id}/{fname}"
                label = f"File {ext.upper()} (formato migliore disponibile)"
                yield log_msg(f"Trovato {label}: {fname}")
                yield log_msg(f"  Download: {fname}")
                try:
                    r = req.get(dl_url, stream=True, timeout=60, verify=False)
                    r.raise_for_status()
                except Exception as e:
                    yield log_msg(f"  ERRORE download {fname}: {e}")
                else:
                    subdir = os.path.join(dest, item_id) if not disk_files else subdir
                    os.makedirs(subdir, exist_ok=True)
                    local = os.path.join(subdir, os.path.basename(fname))
                    with open(local, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    yield log_msg(f"  Salvato: {local}")

                    raw_path = "data/output/raw.txt"
                    if ext == ".txt":
                        import shutil

                        shutil.copy2(local, raw_path)
                        yield log_msg("  Testo già pronto, salto estrazione PDF.")
                    elif ext == ".epub":
                        yield log_msg("  Estrazione testo da EPUB...")
                        try:
                            _extract_epub_text(local, raw_path)
                        except Exception as e:
                            yield log_msg(f"  ERRORE estrazione EPUB: {e}")
                            yield log_msg("  Uso pandoc come fallback...")
                            yield from run_cmd_gen(
                                f'pandoc "{local}" -t plain -o "{raw_path}"'
                            )
                    elif ext in (".html", ".htm"):
                        yield log_msg("  Estrazione testo da HTML...")
                        _extract_html_text(local, raw_path)
                    else:
                        yield log_msg("  Estrazione testo da PDF...")
                        yield from run_cmd_gen(
                            f'python pipeline/pdf2text.py "{local}" "{raw_path}"'
                        )

                    if os.path.exists(raw_path):
                        yield log_msg("Pulizia testo...")
                        yield from run_cmd_gen(
                            f'python pipeline/text_cleaner.py "{raw_path}" "data/output/clean.txt"'
                        )
                        yield log_msg("Generazione dataset...")
                        yield from run_cmd_gen(
                            "python pipeline/build_dataset.py data data/output/dataset_unified.jsonl"
                        )
                    else:
                        yield log_msg("  Nessun testo estratto.")
            else:
                yield log_msg("Nessun file testo/PDF trovato in questo item.")
                if not disk_files:
                    CTRL.running = False
                    return

        elif is_d64:
            yield log_msg("Download D64...")
            r = req.get(url, stream=True, timeout=60, verify=False)
            r.raise_for_status()
            fname = url.split("/")[-1] or "game.d64"
            path = os.path.join(dest, fname)
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            yield log_msg(f"D64 scaricato: {path}")
            yield from run_cmd_gen(f'python pipeline/extract_d64.py "{path}" "{dest}"')

        elif is_g64:
            yield log_msg("Download G64...")
            r = req.get(url, stream=True, timeout=60, verify=False)
            r.raise_for_status()
            fname = url.split("/")[-1] or "disk.g64"
            path = os.path.join(dest, fname)
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            yield log_msg(f"G64 scaricato: {path}")
            yield from run_cmd_gen(f'python pipeline/extract_g64.py "{path}" "{dest}"')

        elif is_prg:
            yield log_msg("Download PRG...")
            r = req.get(url, stream=True, timeout=60, verify=False)
            r.raise_for_status()
            fname = url.split("/")[-1] or "program.prg"
            path = os.path.join(dest, fname)
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            yield log_msg(f"PRG scaricato: {path}")
            yield from run_cmd_gen(f'python pipeline/extract_prg.py "{path}" "{dest}"')

        elif is_gdrive:
            gdrive_dir = os.path.join(dest, "drive_" + folder_id)
            yield log_msg(f"Cerco PDF in {gdrive_dir}...")
            pdfs = []
            if os.path.exists(gdrive_dir):
                for root, _, files in os.walk(gdrive_dir):
                    for fname in files:
                        if fname.lower().endswith(".pdf"):
                            pdfs.append(os.path.join(root, fname))
            yield log_msg(f"  Trovati {len(pdfs)} PDF.")
            if pdfs:
                combined = []
                for i, pdf_path in enumerate(pdfs):
                    tmp = f"data/output/raw_pdf{i}.txt"
                    yield log_msg(
                        f"  [{i + 1}/{len(pdfs)}] {os.path.basename(pdf_path)}"
                    )
                    yield from run_cmd_gen(
                        f'python pipeline/pdf2text.py "{pdf_path}" "{tmp}"'
                    )
                    if os.path.exists(tmp):
                        try:
                            with open(tmp, encoding="utf-8", errors="replace") as f:
                                content = f.read()
                            if content.strip():
                                combined.append(content)
                            else:
                                yield log_msg(f"    (estrazione vuota)")
                        except Exception as e:
                            yield log_msg(f"    (errore lettura: {e})")
                        try:
                            os.remove(tmp)
                        except:
                            pass
                if combined:
                    with open("data/output/raw.txt", "w", encoding="utf-8") as f:
                        f.write("\n\n".join(combined))
                    yield log_msg(
                        f"  Uniti {len(combined)}/{len(pdfs)} PDF con testo, pulizia..."
                    )
                    yield from run_cmd_gen(
                        "python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt"
                    )
                    yield log_msg("Generazione dataset...")
                    yield from run_cmd_gen(
                        "python pipeline/build_dataset.py data data/output/dataset_unified.jsonl"
                    )
                else:
                    yield log_msg("  Nessun PDF con testo estraibile.")
            else:
                yield log_msg("Nessun PDF trovato tra i file scaricati.")

        else:
            yield log_msg("Download PDF...")
            r = req.get(url, stream=True, timeout=30, verify=False)
            r.raise_for_status()
            fname = url.split("/")[-1] or "manual.pdf"
            path = os.path.join(dest, fname)
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            yield log_msg(f"PDF scaricato: {path}")

            yield log_msg("Pipeline estrazione testo...")
            yield from run_cmd_gen("python run_pipeline.py")

        yield log_msg("Ricostruzione KB...")
        if not CTRL.cancelled:
            try:
                kb = C64KnowledgeBase()
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                kb.build_index()
                out = sys.stdout.getvalue()
                sys.stdout = old_stdout
                yield out
            except Exception as e:
                yield log_msg(f"ERRORE KB: {e}")
                CTRL.running = False
                return

        yield log_msg("COMPLETATO")
    else:
        yield log_msg("Cerco PDF nel sito...")
        yield from run_cmd_gen(f'python pipeline/scrape_docs.py "{url}"')
        if CTRL.cancelled:
            return

        yield log_msg("Cerco codice Assembly...")
        yield from run_cmd_gen(f'python pipeline/scrape_url.py "{url}" "web"')
        if CTRL.cancelled:
            return

        yield log_msg("Estrazione PDF trovati...")
        pdfs = []
        for root, _, files in os.walk("data/input"):
            for fname in files:
                if fname.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(root, fname))
                elif fname.lower().endswith(".d64"):
                    yield from run_cmd_gen(
                        f'python pipeline/extract_d64.py "{os.path.join(root, fname)}" "{root}"'
                    )
                elif fname.lower().endswith(".g64"):
                    yield from run_cmd_gen(
                        f'python pipeline/extract_g64.py "{os.path.join(root, fname)}" "{root}"'
                    )
                elif fname.lower().endswith(".prg"):
                    yield from run_cmd_gen(
                        f'python pipeline/extract_prg.py "{os.path.join(root, fname)}" "{root}"'
                    )

        if pdfs:
            combined = []
            for i, pdf_path in enumerate(pdfs):
                tmp = f"data/output/raw_pdf{i}.txt"
                yield log_msg(f"  Elaboro: {os.path.basename(pdf_path)}")
                yield from run_cmd_gen(
                    f'python pipeline/pdf2text.py "{pdf_path}" "{tmp}"'
                )
                if os.path.exists(tmp):
                    with open(tmp) as f:
                        combined.append(f.read())
                    os.remove(tmp)
            with open("data/output/raw.txt", "w") as f:
                f.write("\n\n".join(combined))
            yield log_msg(f"  Uniti {len(pdfs)} PDF in data/output/raw.txt")
            yield log_msg("Pulizia testo...")
            yield from run_cmd_gen(
                "python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt"
            )
            yield log_msg("Generazione dataset...")
            yield from run_cmd_gen(
                "python pipeline/build_dataset.py data data/output/dataset_unified.jsonl"
            )
        else:
            yield log_msg("Nessun PDF trovato.")

        yield log_msg("Ricostruzione KB...")
        if not CTRL.cancelled:
            try:
                kb = C64KnowledgeBase()
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                kb.build_index()
                out = sys.stdout.getvalue()
                sys.stdout = old_stdout
                yield out
            except Exception as e:
                yield log_msg(f"ERRORE KB: {e}")
                return

        yield log_msg("COMPLETATO")

    CTRL.running = False


def on_rebuild():
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        kb = C64KnowledgeBase()
        kb.build_index()
        out = sys.stdout.getvalue()
        return out + "\n[OK] KB ricostruita."
    except Exception as e:
        return f"[ERRORE] {e}"
    finally:
        sys.stdout = old_stdout


def on_process_local():
    """Processa tutti i documenti in data/input e ricostruisce la KB."""
    try:
        from pipeline.process_batch import process_all_pdfs

        yield log_msg("Avvio elaborazione documenti locali in data/input...")

        process_all_pdfs(["data/input"], "data/output")
        yield log_msg("Elaborazione PDF completata. Ricostruisco l'indice...")

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            kb = C64KnowledgeBase()
            kb.build_index()
            out = sys.stdout.getvalue()
            yield (
                out
                + "\n"
                + log_msg("✅ Elaborazione locale completata e KB aggiornata!")
            )
        finally:
            sys.stdout = old_stdout

    except Exception as e:
        yield log_msg(f"❌ ERRORE durante l'elaborazione: {e}")


KB_DIRS = [
    ("knowledge_base", "File Markdown (.md)"),
    ("data/input", "File estratti (.bas.txt, .ml.txt)"),
    ("data/src", "File scraper (.asm)"),
]


def list_kb_files():
    lines = []
    for directory, label in KB_DIRS:
        if not os.path.exists(directory):
            lines.append(f"  {label}: (cartella assente)")
            continue
        files = []
        for root, _, fnames in os.walk(directory):
            for f in fnames:
                fp = os.path.join(root, f)
                sz = os.path.getsize(fp)
                files.append((fp, sz))
        files.sort(key=lambda x: -x[1])
        lines.append(f"\n📁 {label} ({len(files)} file):")
        for fp, sz in files:
            sz_str = (
                f"{sz}B"
                if sz < 1024
                else f"{sz / 1024:.1f}KB"
                if sz < 1048576
                else f"{sz / 1048576:.1f}MB"
            )
            rel = fp[len(directory) + 1 :] if fp.startswith(directory) else fp
            lines.append(f"    {rel:60s} {sz_str:>8s}")
    return "\n".join(lines)


def preview_kb_file(rel_path):
    if not rel_path:
        return "Seleziona un file."
    full_path = None
    if os.path.exists(rel_path):
        full_path = rel_path
    else:
        for directory, _ in KB_DIRS:
            candidate = os.path.join(directory, rel_path)
            if os.path.exists(candidate):
                full_path = candidate
                break
    if not full_path:
        return f"File non trovato: {rel_path}"
    try:
        with open(full_path, "r", errors="replace") as f:
            content = f.read()
        sz = os.path.getsize(full_path)
        lines = content.split("\n")
        preview = "\n".join(lines[:50])
        extra = (
            f"\n\n... ({len(lines) - 50} righe in piu', {sz} byte totali)"
            if len(lines) > 50
            else ""
        )
        return f"--- {rel_path} ({sz} byte) ---\n\n{preview}{extra}"
    except UnicodeDecodeError:
        return f"File binario (non visualizzabile come testo): {rel_path}"
    except Exception as e:
        return f"Errore lettura: {e}"


def all_kb_file_choices():
    choices = []
    for directory, _ in KB_DIRS:
        if not os.path.exists(directory):
            continue
        for root, _, fnames in os.walk(directory):
            for f in fnames:
                rel = os.path.relpath(os.path.join(root, f), directory)
                label = f"{directory}/{rel}"
                choices.append(label)
    return sorted(choices)


def search_kb_files(query):
    if not query:
        return list_kb_files()
    query_lower = query.lower()
    lines = []
    for directory, label in KB_DIRS:
        if not os.path.exists(directory):
            continue
        files = []
        for root, _, fnames in os.walk(directory):
            for f in fnames:
                fp = os.path.join(root, f)
                rel = fp[len(directory) + 1 :] if fp.startswith(directory) else fp
                if query_lower in rel.lower() or query_lower in f.lower():
                    sz = os.path.getsize(fp)
                    files.append((rel, sz))
        if files:
            files.sort(key=lambda x: -x[1])
            lines.append(f"\n📁 {label} ({len(files)} corrispondenze):")
            for rel, sz in files:
                sz_str = (
                    f"{sz}B"
                    if sz < 1024
                    else f"{sz / 1024:.1f}KB"
                    if sz < 1048576
                    else f"{sz / 1048576:.1f}MB"
                )
                lines.append(f"    {rel:60s} {sz_str:>8s}")
    if not lines:
        return f"Nessun file trovato per: {query}"
    return "\n".join(lines)


def on_status():
    lines = []
    for path, label in [
        ("knowledge_base", "File Markdown"),
        ("data/input", "PDF in input"),
        ("data/src", "File scraper"),
        ("data/vectorstore", "Indice vettoriale"),
    ]:
        if os.path.exists(path):
            if path == "data/src":
                n = sum(len(files) for _, _, files in os.walk(path))
            elif path == "data/vectorstore":
                n = len(os.listdir(path))
            else:
                n = len([f for f in os.listdir(path) if not f.startswith(".")])
            lines.append(f"{label}: {n}")
        else:
            lines.append(f"{label}: assente")
    custom = load_custom_sites()
    lines.append(f"Siti personalizzati: {len(custom)}")
    ds_path = "data/output/dataset_unified.jsonl"
    if os.path.exists(ds_path):
        with open(ds_path) as f:
            n = sum(1 for _ in f)
        lines.append(f"Dataset entries: {n}")
    return "\n".join(lines)


PAGE_SIZE = 20


def _fmt_dataset_html(lines, page, query=""):
    import html as _html

    cards = []
    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except Exception:
            continue
        instr = entry.get("instruction", "")
        ctx = entry.get("context", "")
        constraints = entry.get("constraints", [])
        output = entry.get("output", "")
        num = page * PAGE_SIZE + i + 1
        tags = (
            " ".join(
                f'<span style="display:inline-block;background:#334;padding:1px 8px;border-radius:4px;margin:2px;font-size:0.85em;color:#eee">{_html.escape(c)}</span>'
                for c in constraints
            )
            if constraints
            else ""
        )
        card = (
            f'<div style="border:1px solid #555;border-radius:8px;padding:12px;margin:0 6px;'
            f'min-width:360px;max-width:420px;background:#1e1e30;color:#f0f0f0;flex-shrink:0;font-family:sans-serif">'
            f'<div style="color:#888;font-size:0.8em;margin-bottom:4px">#{num}</div>'
            f'<div style="margin-bottom:4px"><strong style="color:#ffd700">Istruzione:</strong><br><span style="color:#ffffff">{_html.escape(instr)}</span></div>'
        )
        if ctx:
            card += f'<div style="margin-bottom:4px"><strong style="color:#ffd700">Contesto:</strong><br><span style="color:#ffffff">{_html.escape(ctx)}</span></div>'
        if tags:
            card += f'<div style="margin-bottom:4px"><strong style="color:#ffd700">Vincoli:</strong><br>{tags}</div>'
        card += (
            f'<pre style="background:#0d0d1a;border:1px solid #333;border-radius:4px;padding:8px;'
            f'margin-top:6px;overflow-x:auto;white-space:pre-wrap;font-size:0.85em;color:#ddd;max-height:300px">{_html.escape(output)}</pre>'
            f"</div>"
        )
        cards.append(card)
    body = "".join(cards)
    return f'<div style="display:flex;overflow-x:auto;gap:4px;padding:8px 0;scrollbar-width:thin">{body}</div>'


def on_view_dataset(page=0, query=""):
    if page is None:
        page = 0
    if query is None:
        query = ""
    path = "data/output/dataset_unified.jsonl"
    if not os.path.exists(path):
        return (
            "<div style='color:#ff6;padding:20px;text-align:center'>Dataset non trovato. Esegui prima la pipeline.</div>",
            0,
            "",
        )
    with open(path) as f:
        lines = f.readlines()
    q = query.strip().lower()
    if q:
        lines = [l for l in lines if q in l.lower()]
    total = len(lines)
    max_page = max(0, (total - 1) // PAGE_SIZE)
    page = max(0, min(int(page), max_page))
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    label = f"Dataset: {total} entries" + (
        f" per '{query.strip()}'" if query.strip() else ""
    )
    header = f'<div style="font-weight:bold;margin-bottom:6px;font-size:1.05em;color:#ddd">{label} | Pagina {page + 1}/{max_page + 1} (righe {start + 1}-{end})</div>'
    body = _fmt_dataset_html(lines[start:end], page, query)
    return header + body, page, query


# ============================================================
# DISTILLAZIONE callback
# ============================================================
DISTILL_CONFIG_PATH = "config/teacher_config.yaml"
DISTILL_PROFILES_PATH = "config/distill_profiles.json"

PREDEFINED_DISTILL_PROFILES = {
    "⚡ Rapido (base)": {
        "backend": "opencode",
        "model": "",
        "types": ["factual", "code", "explain"],
        "languages": ["it", "en"],
        "qa_per_chunk": 2,
        "max_chunks": 50,
        "min_output_len": 20,
        "test_assembly": True,
        "test_basic": True,
    },
    "🇮🇹 Solo Italiano": {
        "backend": "opencode",
        "model": "",
        "types": ["code", "theory"],
        "languages": ["it"],
        "qa_per_chunk": 3,
        "max_chunks": 100,
        "min_output_len": 30,
        "test_assembly": True,
        "test_basic": True,
    },
    "🌍 Completo (tutti i tipi)": {
        "backend": "opencode",
        "model": "",
        "types": ["factual", "code", "explain", "bugfix", "theory"],
        "languages": ["it", "en"],
        "qa_per_chunk": 2,
        "max_chunks": 200,
        "min_output_len": 20,
        "test_assembly": True,
        "test_basic": True,
    },
    "🏋️ Qualità Expert": {
        "backend": "opencode",
        "model": "",
        "types": ["factual", "theory"],
        "languages": ["it", "en"],
        "qa_per_chunk": 1,
        "max_chunks": 30,
        "min_output_len": 50,
        "test_assembly": True,
        "test_basic": True,
    },
    "🔧 Groq Veloce": {
        "backend": "groq",
        "model": "mixtral-8x7b-32768",
        "types": ["factual", "code", "bugfix"],
        "languages": ["en"],
        "qa_per_chunk": 3,
        "max_chunks": 100,
        "min_output_len": 20,
        "test_assembly": True,
        "test_basic": True,
    },
    "🤖 Ollama Locale": {
        "backend": "ollama",
        "model": "llama3",
        "types": ["factual", "code", "explain", "theory"],
        "languages": ["it", "en"],
        "qa_per_chunk": 2,
        "max_chunks": 50,
        "min_output_len": 20,
        "test_assembly": True,
        "test_basic": True,
    },
}


def load_distill_config():
    if not os.path.exists(DISTILL_CONFIG_PATH):
        return {"teacher": {"type": "opencode", "strategy": {}, "quality": {}}}
    with open(DISTILL_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_distill_config(cfg):
    os.makedirs(os.path.dirname(DISTILL_CONFIG_PATH), exist_ok=True)
    with open(DISTILL_CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)


def load_user_distill_profiles():
    if not os.path.exists(DISTILL_PROFILES_PATH):
        return {}
    with open(DISTILL_PROFILES_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_user_distill_profiles(profiles):
    os.makedirs(os.path.dirname(DISTILL_PROFILES_PATH), exist_ok=True)
    with open(DISTILL_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)


def get_distill_profile(name):
    user = load_user_distill_profiles()
    if name in user:
        return user[name]
    return PREDEFINED_DISTILL_PROFILES.get(name)


def get_all_profile_names():
    user = load_user_distill_profiles()
    user_keys = set(user.keys())
    names = [n for n in PREDEFINED_DISTILL_PROFILES if n not in user_keys]
    names.extend(user.keys())
    return names


def on_distill_load_profile(profile_name):
    if not profile_name:
        profile_name = "⚡ Rapido (base)"
    profile = get_distill_profile(profile_name)
    if not profile:
        profile = PREDEFINED_DISTILL_PROFILES["⚡ Rapido (base)"]
    return [
        profile.get("backend", "opencode"),
        profile.get("model", ""),
        "",
        profile.get("types", ["factual", "code", "explain"]),
        profile.get("languages", ["it", "en"]),
        profile.get("qa_per_chunk", 2),
        profile.get("max_chunks", 50),
        profile.get("min_output_len", 20),
        profile.get("test_assembly", True),
        profile.get("test_basic", True),
    ]


def on_distill_save_profile(
    name,
    backend,
    model,
    types,
    languages,
    qa_per_chunk,
    max_chunks,
    min_output_len,
    test_assembly,
    test_basic,
):
    name = name.strip()
    if not name:
        raise gr.Error("Inserisci un nome per il profilo")
    profiles = load_user_distill_profiles()
    profiles[name] = {
        "backend": backend,
        "model": model,
        "types": list(types) if types else [],
        "languages": list(languages) if languages else [],
        "qa_per_chunk": qa_per_chunk,
        "max_chunks": max_chunks,
        "min_output_len": min_output_len,
        "test_assembly": test_assembly,
        "test_basic": test_basic,
    }
    save_user_distill_profiles(profiles)
    names = get_all_profile_names()
    return gr.Dropdown(choices=names, value=name), ""


def on_distill_delete_profile(profile_name):
    if not profile_name:
        raise gr.Error("Seleziona un profilo da eliminare")
    if profile_name in PREDEFINED_DISTILL_PROFILES:
        raise gr.Error("I profili predefiniti non possono essere eliminati")
    profiles = load_user_distill_profiles()
    if profile_name in profiles:
        del profiles[profile_name]
        save_user_distill_profiles(profiles)
    names = get_all_profile_names()
    first = names[0] if names else ""
    return gr.Dropdown(choices=names, value=first)


def on_distill_generate(
    backend,
    model_name,
    api_key,
    types,
    languages,
    qa_per_chunk,
    max_chunks,
    min_output_len,
    test_asm,
    test_basic,
):
    CTRL.reset()
    CTRL.start_time = time.time()
    CTRL.running = True

    cfg = load_distill_config()
    cfg["teacher"]["type"] = backend
    cfg["teacher"]["model"] = model_name
    if api_key:
        cfg["teacher"]["api_key"] = api_key
    cfg["teacher"]["strategy"] = {
        "types": types,
        "languages": languages,
        "qa_per_chunk": qa_per_chunk,
        "max_chunks": max_chunks,
    }
    cfg["teacher"]["quality"] = {
        "min_output_length": min_output_len,
        "test_assembly": test_asm,
        "test_basic": test_basic,
    }
    save_distill_config(cfg)

    cmd = f"python pipeline/knowledge_distiller.py --generate"
    if backend != "opencode":
        cmd += f" --teacher {backend}"
        if model_name:
            cmd += f" --model {model_name}"
    if max_chunks:
        cmd += f" --max-chunks {max_chunks}"

    yield log_msg(f"Avvio distillazione con Teacher: {backend}...")
    for msg in run_cmd_gen(cmd):
        yield msg
        if CTRL.cancelled:
            return

    if not CTRL.cancelled:
        yield log_msg(
            "✅ Dataset distillato generato in data/output/distill_dataset.jsonl"
        )

    CTRL.running = False


def on_distill_train(dataset_path, output_dir, max_seq_length):
    CTRL.reset()
    CTRL.start_time = time.time()
    CTRL.running = True
    log_path = os.path.join(output_dir, "training_log.txt")
    yield log_msg(f"Avvio training LoRA...")
    yield log_msg(f"Log completo salvato in: {log_path}")
    cmd = f"python pipeline/train_lora.py {dataset_path}"
    env = {"OUTPUT_DIR": output_dir, "MAX_SEQ_LENGTH": str(max_seq_length)}
    all_lines = []
    for msg in run_cmd_gen(cmd, env=env):
        yield msg
        all_lines.append(msg)
        if CTRL.cancelled:
            return
    # Save full log to file
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            for line in all_lines:
                f.write(line + "\n")
    except Exception:
        pass
    if not CTRL.cancelled:
        yield log_msg(f"✅ Training completato! Modello salvato in {output_dir}")
    CTRL.running = False


def on_distill_status():
    lines = []
    ds_path = "data/output/distill_dataset.jsonl"
    if os.path.exists(ds_path):
        with open(ds_path) as f:
            n = sum(1 for _ in f)
        lines.append(f"Dataset distillato: {n} entries")
        lines.append(f"Percorso: {ds_path}")
    else:
        lines.append("Dataset distillato: non ancora generato")
    model_dir = "data/models/c64-lora-pro"
    if os.path.exists(model_dir):
        files = os.listdir(model_dir)
        lines.append(f"Modello LoRA: {len(files)} file in {model_dir}")
    else:
        lines.append("Modello LoRA: non ancora addestrato")
    cfg = load_distill_config()
    lines.append(f"Teacher config: type={cfg.get('teacher', {}).get('type', '?')}")
    strategy = cfg.get("teacher", {}).get("strategy", {})
    if strategy:
        lines.append(f"  Tipi: {','.join(strategy.get('types', []))}")
        lines.append(f"  Lingue: {','.join(strategy.get('languages', []))}")
        lines.append(f"  QA/chunk: {strategy.get('qa_per_chunk', '?')}")
        lines.append(f"  Max chunks: {strategy.get('max_chunks', '?')}")
    return "\n".join(lines)


def on_distill_placeholder():
    yield log_msg("Generazione placeholder...")
    from pipeline.knowledge_distiller import KnowledgeDistiller

    d = KnowledgeDistiller()
    d.save_placeholder("data/output/distill_dataset.jsonl")
    yield log_msg("✅ Placeholder salvato")


def scan_lora_checkpoints():
    dirs = []
    base_dirs = ["data/models/c64-lora-pro", "data/models"]
    seen = set()

    def _has_adapter(path):
        return (
            os.path.isdir(path)
            and os.path.exists(os.path.join(path, "adapter_config.json"))
            and (
                os.path.exists(os.path.join(path, "adapter_model.safetensors"))
                or os.path.exists(os.path.join(path, "adapter_model.bin"))
            )
        )

    for base in base_dirs:
        if not os.path.exists(base):
            continue
        # Check if the base dir itself is a valid LoRA checkpoint
        if _has_adapter(base) and base not in seen:
            seen.add(base)
            name = os.path.basename(base)
            dirs.append((name, base))
        # Check subdirectories for checkpoints
        for entry in sorted(os.listdir(base)):
            full = os.path.join(base, entry)
            if not os.path.isdir(full):
                continue
            if _has_adapter(full) and full not in seen:
                seen.add(full)
                dirs.append((entry, full))
    return dirs


def apply_lora(mode, lora_path):
    if mode in ("LoRA", "RAG+LoRA"):
        if not lora_path:
            return "⚠️ Seleziona un checkpoint LoRA dal menu."
        ok = agent.set_lora(lora_path)
        name = os.path.basename(lora_path)
        return f"✅ LoRA attivo: {name}" if ok else f"❌ Errore caricando {name}"
    else:
        agent.unload_lora()
        return "ℹ️ Modello base (nessun LoRA caricato)"


def refresh_lora_list():
    choices = scan_lora_checkpoints()
    return gr.Dropdown(choices=choices, value=None)


def get_lora_status():
    path = agent.active_lora
    if path:
        return f"✅ LoRA: {os.path.basename(path)}"
    return "ℹ️ Modello base"


PROMPT_DATASET_PATH = "data/prompt_dataset.json"
WIKI_GRAPH_PATH = "data/wiki_graph.json"


def load_prompt_dataset():
    if not os.path.exists(PROMPT_DATASET_PATH):
        return []
    with open(PROMPT_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_prompt_dataset(prompts):
    with open(PROMPT_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)


def _prompt_similarity(a, b):
    a_set = set(a.lower().split())
    b_set = set(b.lower().split())
    if not a_set or not b_set:
        return 0.0
    intersection = a_set & b_set
    union = a_set | b_set
    return len(intersection) / len(union)


def add_prompt_with_dedup(text, category="Generale", tags=None, description=""):
    prompts = load_prompt_dataset()
    tags = tags or []
    new_normalized = text.lower().strip().rstrip("?.!")
    for existing in prompts:
        existing_normalized = existing["text"].lower().strip().rstrip("?!.")
        sim = _prompt_similarity(new_normalized, existing_normalized)
        if sim > 0.6:
            return False, f"Prompt troppo simile a: {existing['text']} (sim={sim:.2f})"
    prompts.append({
        "text": text,
        "category": category,
        "tags": tags,
        "description": description,
    })
    save_prompt_dataset(prompts)
    return True, "Prompt aggiunto."


def render_prompt_library_html(category_filter=None):
    prompts = load_prompt_dataset()
    if not prompts:
        return "<p style='color:#888'>Nessun prompt nella libreria.</p>"

    if category_filter:
        prompts = [p for p in prompts if p["category"] == category_filter]

    categories = sorted(set(p["category"] for p in prompts))
    html = []
    for cat in categories:
        cat_prompts = [p for p in prompts if p["category"] == cat]
        html.append(f"<details style='margin-bottom:6px'><summary style='cursor:pointer;font-weight:bold;color:#88ccff'>{cat} ({len(cat_prompts)})</summary>")
        html.append("<div style='display:flex;flex-direction:column;gap:3px;padding:4px 0'>")
        for p in cat_prompts:
            escaped = p["text"].replace("'", "\\'").replace('"', '&quot;')
            title = f"{p['text']}: {p['description']}" if p.get("description") else p["text"]
            html.append(
                f"<button onclick=\"document.querySelector('#prompt-picker input')"
                f"&&document.querySelector('#prompt-picker input').focus()"
                f"||document.querySelector('#prompt-picker textarea')"
                f"&&document.querySelector('#prompt-picker textarea').focus();"
                f"var n=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set||"
                f"Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;"
                f"var e=document.querySelector('#prompt-picker input,#prompt-picker textarea');"
                f"n.call(e,'{escaped}');"
                f"e.dispatchEvent(new Event('input',{{bubbles:true}}));"
                f"e.dispatchEvent(new Event('change',{{bubbles:true}}));"
                f"var b=document.querySelector('#prompt-apply');"
                f"if(b)b.querySelector('button').click();\""
                f" style='display:block;width:100%;text-align:left;padding:5px 8px;"
                f"border:1px solid #444;border-radius:5px;background:#1a1a2e;color:#ddd;"
                f"cursor:pointer;font-size:13px'"
                f" title='{title}'>{p['text']}</button>"
            )
        html.append("</div></details>")
    return "\n".join(html)


def load_wiki_graph():
    if not os.path.exists(WIKI_GRAPH_PATH):
        return {"nodes": [], "edges": []}
    with open(WIKI_GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def render_wiki_graph_html(selected_node=None):
    import json as _json
    graph = load_wiki_graph()
    nodes = graph.get("nodes", [])
    edges_list = graph.get("edges", [])

    colors = {"chip": "#ff6b6b", "software": "#4ecdc4", "concetto": "#45b7d1",
              "registro": "#ffa726", "opcode": "#ab47bc", "basic": "#66bb6a"}

    vis_nodes = []
    for n in nodes:
        c = colors.get(n.get("category", "concetto"), "#888")
        vis_nodes.append({
            "id": n["id"],
            "label": n["label"],
            "color": c,
            "size": 22,
            "category": n.get("category", ""),
            "description": n.get("description", ""),
        })

    vis_edges = []
    for e in edges_list:
        vis_edges.append({"from": e["from"], "to": e["to"], "label": e.get("label", "")})

    nodes_json = _json.dumps(vis_nodes, ensure_ascii=False)
    edges_json = _json.dumps(vis_edges, ensure_ascii=False)

    highlight_js = ""
    if selected_node:
        sel = selected_node.replace("'", "\\'")
        highlight_js = (
            "setTimeout(function(){"
            "network.selectNodes(['%s'],true);"
            "network.focus('%s',{scale:1.5});"
            "},500);" % (sel, sel)
        )

    return """
    <div id="wiki-graph-loading" style="text-align:center;padding:40px;color:#aaa">Caricamento grafo...</div>
    <div id="wiki-graph" style="width:100%;height:600px;border:1px solid #555;border-radius:8px;background:#1a1a2e;display:none"></div>
    <div id="wiki-desc" style="margin-top:8px;padding:12px;border:1px solid #555;border-radius:8px;background:#16213e;min-height:50px;color:#ccc;font-size:14px">Clicca un nodo per vedere la descrizione.</div>
    <script>
    (function(){
        var nodesData = """ + nodes_json + """;
        var edgesData = """ + edges_json + """;
        function initGraph(){
            try {
                var nodes = new vis.DataSet(nodesData);
                var edges = new vis.DataSet(edgesData);
                var container = document.getElementById('wiki-graph');
                document.getElementById('wiki-graph-loading').style.display='none';
                container.style.display='block';
                var data = {nodes:nodes,edges:edges};
                var options = {
                    physics:{barnesHut:{springLength:200,springConstant:0.03,damping:0.1,gravitationalConstant:-5000}},
                    nodes:{shape:'dot',font:{color:'#fff',size:13,face:'monospace'},borderWidth:2,borderWidthSelected:3},
                    edges:{
                        font:{size:10,color:'#aaa',strokeWidth:2,strokeColor:'#1a1a2e'},
                        color:{color:'#999',highlight:'#88ccff',hover:'#88ccff'},
                        width:1.5,smooth:{type:'continuous'}
                    },
                    interaction:{
                        hover:true,tooltipDelay:100,
                        selectable:true,navigationButtons:true,keyboard:true
                    },
                    configure:{filter:['physics']}
                };
                var network = new vis.Network(container, data, options);
                network.on('selectNode', function(params){
                    var nodeId = params.nodes[0];
                    var node = nodes.get(nodeId);
                    var desc = node.description || node.id;
                    document.getElementById('wiki-desc').innerHTML =
                        '<b style="color:#88ccff;font-size:16px">' + node.label + '</b><br>' +
                        '<span style="color:#aaa;font-size:12px">' + (node.category||'') + '</span><br>' +
                        '<span style="color:#ddd">' + desc + '</span>';
                });
                network.on('deselectNode', function(){
                    document.getElementById('wiki-desc').innerHTML = 'Clicca un nodo per vedere la descrizione.';
                });
                """ + highlight_js + """
            } catch(e) {
                document.getElementById('wiki-graph-loading').innerHTML =
                    'Errore: ' + e.message + '. Ricarica la pagina.';
            }
        }
        if(typeof vis !== 'undefined'){initGraph();}else{
            var s=document.createElement('script');
            s.onload=initGraph;
            s.onerror=function(){
                document.getElementById('wiki-graph-loading').innerHTML =
                    'Impossibile caricare la libreria vis.js. Verifica la connessione internet.';
            };
            s.src='https://cdn.jsdelivr.net/npm/vis-network@9.1.6/dist/vis-network.min.js';
            document.head.appendChild(s);
        }
        setTimeout(function(){
            var el=document.getElementById('wiki-graph-loading');
            if(el && el.style.display!='none'){
                el.innerHTML='Tempo scaduto. Verifica la connessione internet o ricarica.';
            }
        },8000);
    })();
    </script>
    """


def bootstrap():
    """Crea le cartelle necessarie se non esistono."""
    dirs = [
        "data/input",
        "data/output",
        "data/tmp",
        "data/models",
        "data/src",
        "data/vectorstore",
        "knowledge_base",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print(f"Bootstrap completato: {len(dirs)} cartelle verificate/create.")


def launch_ui():
    global agent
    bootstrap()
    lora = os.environ.get("LORA_PATH")
    gguf = os.environ.get("GGUF_MODEL_PATH")

    agent = C64CodingAgent(lora_path=lora, gguf_path=gguf)
    pm = agent.pm

    with gr.Blocks(title="C64 Coding Agent PRO") as demo:
        with gr.Tab("Chat"):
            gr.Markdown("# C64 Coding Agent PRO")
            gr.Markdown(
                "Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato."
            )

            with gr.Row():
                with gr.Column(scale=4):
                    chat_interface = gr.ChatInterface(
                        agent.chat_wrapper,
                        additional_inputs=[
                            mode_radio := gr.Radio(
                                ["Base", "RAG", "LoRA", "RAG+LoRA"],
                                value="RAG",
                                label="Modalità",
                            ),
                            auto_scrape_box := gr.Checkbox(
                                label="Auto-elabora link (aggiungi siti + pipeline)",
                                value=False,
                            ),
                        ],
                    )
                with gr.Column(scale=1):
                    gr.Markdown("### LoRA")
                    lora_dropdown = gr.Dropdown(
                        choices=scan_lora_checkpoints(),
                        label="Checkpoint",
                    )
                    with gr.Row():
                        apply_lora_btn = gr.Button(
                            "Applica LoRA", size="sm", variant="primary"
                        )
                        refresh_lora_btn = gr.Button("🔄", size="sm")
                    lora_status_box = gr.Textbox(
                        value=get_lora_status(),
                        label="Stato",
                        lines=1,
                    )

                    hints_md = gr.Markdown(
                        value="",
                        label="Riferimenti",
                    )

                    gr.Markdown("### Prompt Library")
                    prompt_html = gr.HTML(render_prompt_library_html())
                    prompt_picker = gr.Textbox(
                        visible=False, elem_id="prompt-picker"
                    )
                    prompt_apply = gr.Button(
                        "Apply", visible=False, elem_id="prompt-apply"
                    )
                    prompt_apply.click(
                        fn=lambda x: x,
                        inputs=prompt_picker,
                        outputs=chat_interface.textbox,
                    )

                    category_filter = gr.Radio(
                        choices=["Tutti", "Assembly", "BASIC", "Grafica", "Suono", "Sistema", "Memoria"],
                        value="Tutti",
                        label="Categoria",
                    )
                    category_filter.change(
                        fn=lambda c: render_prompt_library_html(None if c == "Tutti" else c),
                        inputs=category_filter,
                        outputs=prompt_html,
                    )

            apply_lora_btn.click(
                fn=apply_lora,
                inputs=[mode_radio, lora_dropdown],
                outputs=lora_status_box,
            )
            refresh_lora_btn.click(
                fn=refresh_lora_list,
                outputs=lora_dropdown,
            )

            chat_interface.textbox.submit(
                fn=get_hints, inputs=chat_interface.textbox, outputs=hints_md
            )

        def on_scrape_batch(selected):
            CTRL.reset()
            CTRL.start_time = time.time()
            CTRL.running = True
            if not selected:
                yield "Seleziona almeno un sito."
                CTRL.running = False
                return
            predefined_names = {k for k, _ in PREDEFINED}
            predefined_sel = [s for s in selected if s in predefined_names]
            custom_sites = load_custom_sites()
            custom_sel = [s for s in custom_sites if s["name"] in selected]

            for s in predefined_sel:
                if CTRL.cancelled:
                    yield log_msg("ANNULLATO")
                    break
                yield log_msg(f"Scraping: {s}")
                yield from run_cmd_gen(
                    f"python pipeline/c64_asm_scraper.py --sites {s} --delay 1.5"
                )

            for s in custom_sel:
                if CTRL.cancelled:
                    yield log_msg("ANNULLATO")
                    break
                yield log_msg(f"Scraping: {s['name']}")
                yield log_msg("  Cerco PDF...")
                yield from run_cmd_gen(f'python pipeline/scrape_docs.py "{s["url"]}"')
                if CTRL.cancelled:
                    yield log_msg("ANNULLATO")
                    break
                yield log_msg("  Cerco codice Assembly...")
                yield from run_cmd_gen(
                    f'python pipeline/scrape_url.py "{s["url"]}" "{s["name"]}"'
                )

            if not CTRL.cancelled:
                yield log_msg("Estrazione testo da PDF...")
                pdfs = []
                for root, _, files in os.walk("data/input"):
                    for fname in files:
                        if fname.lower().endswith(".pdf"):
                            pdfs.append(os.path.join(root, fname))
                if pdfs:
                    combined = []
                    for i, pdf_path in enumerate(pdfs):
                        tmp = f"data/output/raw_pdf{i}.txt"
                        yield log_msg(f"  Elaboro: {os.path.basename(pdf_path)}")
                        yield from run_cmd_gen(
                            f'python pipeline/pdf2text.py "{pdf_path}" "{tmp}"'
                        )
                        if os.path.exists(tmp):
                            with open(tmp) as f:
                                combined.append(f.read())
                            os.remove(tmp)
                    with open("data/output/raw.txt", "w") as f:
                        f.write("\n\n".join(combined))
                    yield log_msg(f"  Uniti {len(pdfs)} PDF in data/output/raw.txt")
                    yield log_msg("Pulizia testo...")
                    yield from run_cmd_gen(
                        "python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt"
                    )
                    yield log_msg("Generazione dataset...")
                    yield from run_cmd_gen(
                        "python pipeline/build_dataset.py data data/output/dataset_unified.jsonl"
                    )
                else:
                    yield log_msg("Nessun PDF da processare.")

                yield log_msg("Ricostruisco KB...")
                try:
                    kb = C64KnowledgeBase()
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()
                    kb.build_index()
                    out = sys.stdout.getvalue()
                    sys.stdout = old_stdout
                    yield out + log_msg("KB aggiornata.")
                except Exception as e:
                    yield f"[ERRORE] KB: {e}"
            CTRL.running = False

        with gr.Tab("Scarica e Siti"):
            gr.Markdown("## Scarica URL")
            with gr.Row():
                with gr.Column(scale=2):
                    url_input = gr.Textbox(
                        label="URL",
                        placeholder="https://...manuale.pdf  o  archive.org/details/...  o  https://drive.google.com/drive/folders/...",
                    )
                    with gr.Row():
                        download_btn = gr.Button(
                            "Scarica URL", variant="primary", size="sm"
                        )

                    gr.Markdown("## Scrapa Siti")
                    site_list = gr.CheckboxGroup(
                        choices=all_site_choices(),
                        label="Seleziona siti da scrapare",
                        value=[],
                    )
                    with gr.Row():
                        scrape_btn = gr.Button(
                            "Scrapa Selezionati", variant="primary", size="sm"
                        )

                    with gr.Row():
                        pause_btn = gr.Button("Pausa", size="sm")
                        resume_btn = gr.Button("Riprendi", size="sm")
                        cancel_btn = gr.Button("Annulla", variant="stop", size="sm")

                    main_log = gr.Textbox(label="Log", lines=18, max_lines=40)

                    def on_download_only(url):
                        if not url:
                            yield "Inserisci un URL."
                            return
                        CTRL.reset()
                        CTRL.start_time = time.time()
                        CTRL.running = True
                        for msg in download_and_integrate(url):
                            yield msg
                            if CTRL.cancelled:
                                yield log_msg("ANNULLATO")
                                break
                        if not CTRL.cancelled:
                            yield log_msg("COMPLETATO")
                        CTRL.running = False

                    def on_scrape_only(sites):
                        for msg in on_scrape_batch(sites):
                            yield msg

                    download_btn.click(
                        fn=on_download_only, inputs=url_input, outputs=main_log
                    )
                    scrape_btn.click(
                        fn=on_scrape_only, inputs=site_list, outputs=main_log
                    )
                    pause_btn.click(fn=CTRL.pause, outputs=[], queue=False)
                    resume_btn.click(fn=CTRL.resume, outputs=[], queue=False)
                    cancel_btn.click(fn=CTRL.cancel, outputs=[], queue=False)

                with gr.Column(scale=1):
                    gr.Markdown("### Gestione siti")
                    new_name = gr.Textbox(label="Nome", placeholder="es. mio-sito-c64")
                    new_url = gr.Textbox(
                        label="URL", placeholder="https://nuovo-sito-c64.it/"
                    )
                    add_btn = gr.Button("Aggiungi", size="sm")
                    add_msg = gr.Textbox(label="", lines=1)
                    del_dropdown = gr.Dropdown(
                        choices=[s["name"] for s in load_custom_sites()],
                        label="Rimuovi sito",
                    )
                    del_btn = gr.Button("Rimuovi", variant="stop", size="sm")
                    del_msg = gr.Textbox(label="", lines=1)

                    def on_add_site(name, url):
                        if not name or not url:
                            return "Inserisci nome e URL.", gr.CheckboxGroup(
                                choices=all_site_choices()
                            )
                        save_custom_site(name.strip(), url.strip())
                        return f"Sito '{name}' aggiunto!", gr.CheckboxGroup(
                            choices=all_site_choices()
                        )

                    def on_del_site(name):
                        if not name:
                            return (
                                "Seleziona un sito da rimuovere.",
                                gr.Dropdown(
                                    choices=[s["name"] for s in load_custom_sites()]
                                ),
                                gr.CheckboxGroup(choices=all_site_choices()),
                            )
                        remove_custom_site(name)
                        remaining = [s["name"] for s in load_custom_sites()]
                        return (
                            f"Sito '{name}' rimosso!",
                            gr.Dropdown(choices=remaining),
                            gr.CheckboxGroup(choices=all_site_choices()),
                        )

                    add_btn.click(
                        fn=on_add_site,
                        inputs=[new_name, new_url],
                        outputs=[add_msg, site_list],
                    )
                    del_btn.click(
                        fn=on_del_site,
                        inputs=del_dropdown,
                        outputs=[del_msg, del_dropdown, site_list],
                    )

        with gr.Tab("Knowledge Base"):
            gr.Markdown("## Knowledge Base")
            kb_log = gr.Textbox(label="", lines=16)

            with gr.Row():
                with gr.Column(scale=1):
                    process_local_btn = gr.Button(
                        "📂 Processa Documenti Locali (data/input)", variant="primary"
                    )
                    rebuild_btn = gr.Button(
                        "Ricostruisci solo Indice", variant="secondary"
                    )

                    process_local_btn.click(fn=on_process_local, outputs=kb_log)
                    rebuild_btn.click(fn=on_rebuild, outputs=kb_log)

                with gr.Column(scale=2):
                    gr.Markdown("### Esplora file KB")
                    with gr.Row():
                        list_btn = gr.Button("Elenca tutti i file", size="sm")
                        search_input = gr.Textbox(
                            label="Cerca file",
                            placeholder="Inserisci parte del nome file...",
                            scale=3,
                        )
                        search_btn = gr.Button("Cerca", size="sm")
                    file_dropdown = gr.Dropdown(
                        choices=all_kb_file_choices(),
                        label="Anteprima file",
                    )
                    preview_btn = gr.Button("Visualizza", size="sm")

            list_btn.click(fn=list_kb_files, outputs=kb_log)
            search_btn.click(fn=search_kb_files, inputs=search_input, outputs=kb_log)
            preview_btn.click(fn=preview_kb_file, inputs=file_dropdown, outputs=kb_log)

        with gr.Tab("Dati"):
            gr.Markdown("## Gestione dataset e statistiche")

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### Dataset")
                    dataset_page = gr.State(0)
                    dataset_query = gr.State("")
                    with gr.Row(equal_height=True):
                        prev_btn = gr.Button("◀ Precedente", min_width=120)
                        dataset_btn = gr.Button(
                            "Visualizza Dataset", variant="primary", min_width=160
                        )
                        next_btn = gr.Button("Successiva ▶", min_width=120)
                    with gr.Row():
                        ds_search = gr.Textbox(
                            label="Cerca nel Dataset",
                            placeholder="Termine di ricerca...",
                            scale=3,
                        )
                        ds_search_btn = gr.Button("Cerca", size="sm")
                    ds_output = gr.HTML(label="Dataset")
                    dataset_btn.click(
                        fn=lambda: on_view_dataset(0, ""),
                        outputs=[ds_output, dataset_page, dataset_query],
                    )
                    prev_btn.click(
                        fn=lambda p, q: on_view_dataset(int(p or 0) - 1, q),
                        inputs=[dataset_page, dataset_query],
                        outputs=[ds_output, dataset_page, dataset_query],
                    )
                    next_btn.click(
                        fn=lambda p, q: on_view_dataset(int(p or 0) + 1, q),
                        inputs=[dataset_page, dataset_query],
                        outputs=[ds_output, dataset_page, dataset_query],
                    )
                    ds_search_btn.click(
                        fn=lambda q: on_view_dataset(0, q),
                        inputs=ds_search,
                        outputs=[ds_output, dataset_page, dataset_query],
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### Statistiche")
                    info_log = gr.Textbox(label="", lines=16)
                    status_btn = gr.Button("Aggiorna")
                    status_btn.click(fn=on_status, outputs=info_log)

        with gr.Tab("Distillazione"):
            gr.Markdown("## Knowledge Distillation — Teacher → Student")
            gr.Markdown(
                "Genera un dataset sintetico di alta qualità usando un Teacher LLM, "
                "poi addestra Qwen2.5-Coder-1.5B via LoRA. "
                "Teacher predefinito: **OpenCode** (nessuna API key necessaria)."
            )

            # === Profili di Configurazione ===
            gr.Markdown("### Profili di Configurazione")
            gr.Markdown(
                "Seleziona un profilo predefinito o personalizzato per impostare "
                "automaticamente tutti i parametri. Crea nuovi profili con **Salva**."
            )
            with gr.Row():
                profile_dropdown = gr.Dropdown(
                    choices=get_all_profile_names(),
                    value=get_all_profile_names()[0]
                    if get_all_profile_names()
                    else None,
                    label="Profilo",
                    interactive=True,
                )
                profile_save_name = gr.Textbox(
                    label="Salva come...",
                    placeholder="Nome nuovo profilo",
                    scale=2,
                )
                profile_save_btn = gr.Button("💾 Salva", size="sm")
                profile_delete_btn = gr.Button("🗑️ Elimina", size="sm")

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### Configurazione Teacher")

                    teacher_backend = gr.Dropdown(
                        choices=[
                            ("OpenCode (gratuito, built-in)", "opencode"),
                            ("Groq (gratuito, veloce)", "groq"),
                            ("OpenRouter (modelli vari)", "openrouter"),
                            ("Ollama (locale)", "ollama"),
                            ("HuggingFace Inference API", "huggingface"),
                        ],
                        value="opencode",
                        label="Backend Teacher",
                    )
                    teacher_model = gr.Textbox(
                        label="Modello Teacher (opzionale)",
                        placeholder="es. qwen/qwen3-32b, llama3-70b-8192",
                        value="",
                    )
                    teacher_api_key = gr.Textbox(
                        label="API Key (solo per Groq/OpenRouter/HF)",
                        placeholder="sk-... o lascia vuoto se usi .env",
                        type="password",
                        value="",
                    )

                    gr.Markdown("### Strategia di generazione")
                    with gr.Row():
                        type_checkboxes = gr.CheckboxGroup(
                            choices=[
                                ("Factual Q&A", "factual"),
                                ("Code Generation", "code"),
                                ("Code Explanation", "explain"),
                                ("Bug Fixing", "bugfix"),
                                ("Theory", "theory"),
                            ],
                            value=["factual", "code", "explain"],
                            label="Tipi di dato",
                        )
                        lang_checkboxes = gr.CheckboxGroup(
                            choices=[("Italiano", "it"), ("English", "en")],
                            value=["it", "en"],
                            label="Lingue",
                        )
                    with gr.Row():
                        qa_per_chunk = gr.Slider(
                            1, 5, value=2, step=1, label="QA per chunk"
                        )
                        max_chunks = gr.Slider(
                            10, 500, value=50, step=10, label="Max chunks"
                        )
                    with gr.Accordion("Filtri qualità", open=False):
                        min_output_len = gr.Slider(
                            10, 200, value=20, step=5, label="Lunghezza minima risposta"
                        )
                        test_assembly = gr.Checkbox(
                            label="Testa Assembly con ACME", value=True
                        )
                        test_basic = gr.Checkbox(
                            label="Testa BASIC sintatticamente", value=True
                        )

                    with gr.Row():
                        generate_btn = gr.Button(
                            "🚀 Genera Dataset", variant="primary", size="sm"
                        )
                        placeholder_btn = gr.Button(
                            "📄 Placeholder (1 esempio)", size="sm"
                        )

                with gr.Column(scale=2):
                    gr.Markdown("### Training LoRA")
                    train_dataset = gr.Textbox(
                        label="Dataset path",
                        value="data/output/distill_dataset.jsonl",
                    )
                    train_output = gr.Textbox(
                        label="Output dir",
                        value="data/models/c64-lora-pro",
                    )
                    train_seq_len = gr.Slider(
                        512,
                        4096,
                        value=512,
                        step=256,
                        label="Max sequence length (512 per CPU, 2048+ per GPU)",
                    )
                    train_btn = gr.Button(
                        "🏋️ Addestra (LoRA)", variant="primary", size="sm"
                    )

                    gr.Markdown("### Stato")
                    distill_status_btn = gr.Button("📊 Stato", size="sm")
                    distill_log = gr.Textbox(label="Log", lines=20, max_lines=40)

            # === Eventi Profili ===
            profile_dropdown.change(
                fn=on_distill_load_profile,
                inputs=profile_dropdown,
                outputs=[
                    teacher_backend,
                    teacher_model,
                    teacher_api_key,
                    type_checkboxes,
                    lang_checkboxes,
                    qa_per_chunk,
                    max_chunks,
                    min_output_len,
                    test_assembly,
                    test_basic,
                ],
            )
            profile_save_btn.click(
                fn=on_distill_save_profile,
                inputs=[
                    profile_save_name,
                    teacher_backend,
                    teacher_model,
                    type_checkboxes,
                    lang_checkboxes,
                    qa_per_chunk,
                    max_chunks,
                    min_output_len,
                    test_assembly,
                    test_basic,
                ],
                outputs=[profile_dropdown, profile_save_name],
            )
            profile_delete_btn.click(
                fn=on_distill_delete_profile,
                inputs=profile_dropdown,
                outputs=profile_dropdown,
            )

            # === Eventi Generazione / Training ===
            generate_btn.click(
                fn=on_distill_generate,
                inputs=[
                    teacher_backend,
                    teacher_model,
                    teacher_api_key,
                    type_checkboxes,
                    lang_checkboxes,
                    qa_per_chunk,
                    max_chunks,
                    min_output_len,
                    test_assembly,
                    test_basic,
                ],
                outputs=distill_log,
            )
            placeholder_btn.click(
                fn=on_distill_placeholder,
                outputs=distill_log,
            )
            train_btn.click(
                fn=on_distill_train,
                inputs=[train_dataset, train_output, train_seq_len],
                outputs=distill_log,
            )
            distill_status_btn.click(
                fn=on_distill_status,
                outputs=distill_log,
            )

        with gr.Tab("Grafo Wiki"):
            gr.Markdown("## Grafo della Conoscenza C64")
            gr.Markdown(
                "Esplora le connessioni tra chip, registri, opcode e concetti del Commodore 64. "
                "Clicca un nodo per vedere la descrizione."
            )
            wiki_graph_html = gr.HTML(render_wiki_graph_html())
            wiki_search = gr.Textbox(
                label="Cerca nodo",
                placeholder="es. VIC-II, $D020, sprite...",
            )
            wiki_search.submit(
                fn=lambda q: render_wiki_graph_html(q if q else None),
                inputs=wiki_search,
                outputs=wiki_graph_html,
            )
            wiki_reset = gr.Button("Reimposta grafo")
            wiki_reset.click(
                fn=lambda: render_wiki_graph_html(None),
                outputs=wiki_graph_html,
            )

    demo.launch(server_name="0.0.0.0", theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_ui()

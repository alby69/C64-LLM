import os
import sys
import subprocess
import time
import re
import json
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
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGSTOP)

    def resume(self):
        self.pause_event.set()
        if self.proc and self.proc.poll() is None:
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
    name = re.sub(r'^www\.', '', parsed.netloc or parsed.path)
    return name[:50]


class C64CodingAgent:
    def __init__(self, base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct", lora_path=None, gguf_path=None):
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
                self.tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(
                    base_model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True
                )

                if lora_path and os.path.exists(lora_path):
                    print(f"Loading LoRA from: {lora_path}")
                    model = PeftModel.from_pretrained(model, lora_path)

                self.backend = ModelBackend(model, self.tokenizer)
            except Exception as e:
                print(f"Error loading model with transformers: {e}")
                print("Falling back to CPU-only mode (Mock/GGUF placeholder if path missing)")
                self.backend = LlamaCppBackend(gguf_path)
                self.tokenizer = None

        self.pm = PromptManager()
        self.orchestrator = OrchestratorAgent(self.backend, self.tokenizer, pm=self.pm)

    def chat_wrapper(self, message, history, use_rag, auto_scrape, max_attempts):
        formatted_history: list[tuple[str, str]] = []
        for item in history:
            if isinstance(item, dict):
                formatted_history.append((item.get("content", ""), ""))
            elif len(item) >= 2:
                formatted_history.append((str(item[0]), str(item[1])))
            else:
                formatted_history.append((str(item), ""))

        try:
            response, sources, logs = self.orchestrator.process_request(
                message,
                use_rag=use_rag,
                chat_history=formatted_history,
                max_attempts=int(max_attempts)
            )

            source_text = ""
            if sources:
                source_text = "\n\n**Fonti consultate:**\n" + "\n".join([f"- {s}" for s in set(sources)])

            log_text = ""
            if logs:
                log_text = "\n\n<details><summary>Pensieri dell'Agente (Logs)</summary>\n\n" + "\n".join([f"- {l}" for l in logs]) + "\n</details>"

            base = response + source_text + log_text
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
                yield base + f"\n\n---\n📌 **{added} nuovi siti aggiunti.** Avvio pipeline..."
            else:
                yield base + "\n\n---\n📌 **Siti già presenti.** Avvio pipeline..."

            for idx, url in enumerate(all_urls, 1):
                yield base + f"\n\n---\n🔄 **[{idx}/{len(all_urls)}]** {_domain_name(url)}"
                last, count = "", 0
                for msg in download_and_integrate(url):
                    last, count = msg, count + 1
                    if count % 5 == 0:
                        yield base + f"\n\n---\n🔄 **{_domain_name(url)}**\n{last}"
                yield base + f"\n\n---\n✅ **[{idx}/{len(all_urls)}]** {_domain_name(url)}\n{last}"

            yield base + f"\n\n---\n✅ **Pipeline completata per {len(all_urls)} URL — KB aggiornata!**"

        except Exception as e:
            yield f"Errore durante l'elaborazione: {str(e)}"


def log_msg(msg):
    return f"[{CTRL.elapsed()}] {msg}"


def run_cmd_gen(cmd):
    yield log_msg(f"Avvio: {cmd}")
    CTRL.check_pause()
    if CTRL.cancelled:
        yield log_msg("ANNULLATO")
        return
    try:
        CTRL.proc = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, preexec_fn=os.setsid
        )
        lines = []
        for line in iter(CTRL.proc.stdout.readline, ""):
            CTRL.check_pause()
            if CTRL.cancelled:
                CTRL.proc.kill()
                yield log_msg("ANNULLATO")
                return
            lines.append(line.rstrip())
            yield "\n".join(lines[-80:])
        CTRL.proc.wait()
        if CTRL.proc.returncode != 0:
            lines.append(log_msg(f"ERRORE: codice {CTRL.proc.returncode}"))
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
        match = re.search(r'/drive/folders/([^/?]+)', url)
        if not match:
            yield log_msg("URL Google Drive non valido."); return
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
            yield log_msg("  ⚠ Nessun file trovato. Verifica che la cartella sia pubblica.")
        else:
            dirs_map: dict[str, list] = {}
            for f in files_info:
                p = os.path.dirname(f.local_path)
                dirs_map.setdefault(p, []).append(f)
            yield log_msg(f"  Trovati {len(files_info)} file in {len(dirs_map)} sottocartelle:")
            for d, flist in sorted(dirs_map.items()):
                rel = os.path.relpath(d, out_dir)
                if rel == ".":
                    rel = "(radice)"
                yield log_msg(f"    [{len(flist):2d}] {rel}")
            yield log_msg("  Download in corso... (file grandi potrebbero richiedere tempo)")
            ok = 0
            err = 0
            skip = 0
            for i, f in enumerate(files_info, 1):
                os.makedirs(os.path.dirname(f.local_path), exist_ok=True)
                fname = os.path.basename(f.local_path)
                if os.path.exists(f.local_path):
                    sz = os.path.getsize(f.local_path)
                    yield log_msg(f"  [{i:3d}/{len(files_info)}] {fname}  — {sz/1024/1024:.1f} MB (già presente)")
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
                        r = req.get(direct_url, stream=True, timeout=120, allow_redirects=True)
                        if r.status_code == 200 and "text/html" not in r.headers.get("content-type", ""):
                            with open(f.local_path, "wb") as fout:
                                for chunk in r.iter_content(8192):
                                    fout.write(chunk)
                            downloaded = True
                    except Exception:
                        pass
                if downloaded:
                    sz = os.path.getsize(f.local_path)
                    yield log_msg(f"  [{i:3d}/{len(files_info)}] {fname}  — {sz/1024/1024:.1f} MB ✓")
                    ok += 1
                else:
                    yield log_msg(f"  [{i:3d}/{len(files_info)}] {fname}  — ERRORE download ✗")
                    err += 1
                if i < len(files_info):
                    time.sleep(1.5)
            yield log_msg(f"  ══ Riepilogo: {ok} scaricati, {skip} già presenti, {err} errori ══")

    if is_pdf or is_d64 or is_prg or is_g64 or is_archive or is_gdrive:
        dest = "data/input"
        os.makedirs(dest, exist_ok=True)

        if is_archive:
            yield log_msg("Analizzo contenuto Archive.org...")
            from agent.crawler import WebCrawlerAgent
            import json as _json
            match = re.search(r'details/([^/?]+)', url)
            if not match:
                yield log_msg("URL Archive.org non valido."); return
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
                        yield from run_cmd_gen(f"python pipeline/extract_d64.py \"{local}\" \"{subdir}\"")
                    elif ext == ".g64":
                        yield from run_cmd_gen(f"python pipeline/extract_g64.py \"{local}\" \"{subdir}\"")
                    elif ext == ".prg":
                        yield from run_cmd_gen(f"python pipeline/extract_prg.py \"{local}\" \"{subdir}\"")

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
                            yield from run_cmd_gen(f"pandoc \"{local}\" -t plain -o \"{raw_path}\"")
                    elif ext in (".html", ".htm"):
                        yield log_msg("  Estrazione testo da HTML...")
                        _extract_html_text(local, raw_path)
                    else:
                        yield log_msg("  Estrazione testo da PDF...")
                        yield from run_cmd_gen(f"python pipeline/pdf2text.py \"{local}\" \"{raw_path}\"")

                    if os.path.exists(raw_path):
                        yield log_msg("Pulizia testo...")
                        yield from run_cmd_gen(f"python pipeline/text_cleaner.py \"{raw_path}\" \"data/output/clean.txt\"")
                        yield log_msg("Generazione dataset...")
                        yield from run_cmd_gen("python pipeline/build_dataset.py data data/output/dataset_unified.jsonl")
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
            yield from run_cmd_gen(f"python pipeline/extract_d64.py \"{path}\" \"{dest}\"")

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
            yield from run_cmd_gen(f"python pipeline/extract_g64.py \"{path}\" \"{dest}\"")

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
            yield from run_cmd_gen(f"python pipeline/extract_prg.py \"{path}\" \"{dest}\"")

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
                    yield log_msg(f"  [{i+1}/{len(pdfs)}] {os.path.basename(pdf_path)}")
                    yield from run_cmd_gen(f"python pipeline/pdf2text.py \"{pdf_path}\" \"{tmp}\"")
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
                    yield log_msg(f"  Uniti {len(combined)}/{len(pdfs)} PDF con testo, pulizia...")
                    yield from run_cmd_gen("python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt")
                    yield log_msg("Generazione dataset...")
                    yield from run_cmd_gen("python pipeline/build_dataset.py data data/output/dataset_unified.jsonl")
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
                    yield from run_cmd_gen(f"python pipeline/extract_d64.py \"{os.path.join(root, fname)}\" \"{root}\"")
                elif fname.lower().endswith(".g64"):
                    yield from run_cmd_gen(f"python pipeline/extract_g64.py \"{os.path.join(root, fname)}\" \"{root}\"")
                elif fname.lower().endswith(".prg"):
                    yield from run_cmd_gen(f"python pipeline/extract_prg.py \"{os.path.join(root, fname)}\" \"{root}\"")

        if pdfs:
            combined = []
            for i, pdf_path in enumerate(pdfs):
                tmp = f"data/output/raw_pdf{i}.txt"
                yield log_msg(f"  Elaboro: {os.path.basename(pdf_path)}")
                yield from run_cmd_gen(f"python pipeline/pdf2text.py \"{pdf_path}\" \"{tmp}\"")
                if os.path.exists(tmp):
                    with open(tmp) as f:
                        combined.append(f.read())
                    os.remove(tmp)
            with open("data/output/raw.txt", "w") as f:
                f.write("\n\n".join(combined))
            yield log_msg(f"  Uniti {len(pdfs)} PDF in data/output/raw.txt")
            yield log_msg("Pulizia testo...")
            yield from run_cmd_gen("python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt")
            yield log_msg("Generazione dataset...")
            yield from run_cmd_gen("python pipeline/build_dataset.py data data/output/dataset_unified.jsonl")
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
                yield log_msg(f"ERRORE KB: {e}"); return

        yield log_msg("COMPLETATO")

    CTRL.running = False


def on_rebuild():
    try:
        kb = C64KnowledgeBase()
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        kb.build_index()
        out = sys.stdout.getvalue()
        sys.stdout = old_stdout
        return out + "\n[OK] KB ricostruita."
    except Exception as e:
        return f"[ERRORE] {e}"


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
            sz_str = f"{sz}B" if sz < 1024 else f"{sz/1024:.1f}KB" if sz < 1048576 else f"{sz/1048576:.1f}MB"
            rel = fp[len(directory)+1:] if fp.startswith(directory) else fp
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
        extra = f"\n\n... ({len(lines) - 50} righe in piu', {sz} byte totali)" if len(lines) > 50 else ""
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
                rel = fp[len(directory)+1:] if fp.startswith(directory) else fp
                if query_lower in rel.lower() or query_lower in f.lower():
                    sz = os.path.getsize(fp)
                    files.append((rel, sz))
        if files:
            files.sort(key=lambda x: -x[1])
            lines.append(f"\n📁 {label} ({len(files)} corrispondenze):")
            for rel, sz in files:
                sz_str = f"{sz}B" if sz < 1024 else f"{sz/1024:.1f}KB" if sz < 1048576 else f"{sz/1048576:.1f}MB"
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
        tags = " ".join(
            f'<span style="display:inline-block;background:#334;padding:1px 8px;border-radius:4px;margin:2px;font-size:0.85em;color:#eee">{_html.escape(c)}</span>'
            for c in constraints
        ) if constraints else ""
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
            f'</div>'
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
        return "<div style='color:#ff6;padding:20px;text-align:center'>Dataset non trovato. Esegui prima la pipeline.</div>", 0, ""
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
    label = f"Dataset: {total} entries" + (f" per '{query.strip()}'" if query.strip() else "")
    header = f'<div style="font-weight:bold;margin-bottom:6px;font-size:1.05em;color:#ddd">{label} | Pagina {page+1}/{max_page+1} (righe {start+1}-{end})</div>'
    body = _fmt_dataset_html(lines[start:end], page, query)
    return header + body, page, query


TECHNICAL_TERMS = {
    "$D020": 5, "$D021": 4, "$D022": 2, "$D023": 2,
    "$D011": 4, "$D012": 5, "$D013": 2, "$D01A": 3,
    "$D019": 3, "$D01E": 2, "$D01F": 2, "$D01D": 2,
    "$D400": 3, "$D418": 3, "$D41B": 2,
    "$D800": 4, "$D81D": 2,
    "$DC00": 3, "$DC01": 3, "$DC0D": 2,
    "$DD00": 3, "$DD0D": 2,
    "$0314": 4, "$0315": 3,
    "$FFD2": 4, "$FFE4": 3, "$FFCF": 2, "$FF81": 2,
    "VIC-II": 5, "SID": 5, "CIA": 4, "KERNAL": 5,
    "Zero Page": 4, "Stack Pointer": 3, "Program Counter": 3,
    "Accumulator": 4, "X Register": 3, "Y Register": 3,
    "Status Register": 3, "Carry Flag": 3, "Zero Flag": 3,
    "Interrupt Flag": 2, "Decimal Flag": 2, "Overflow Flag": 2,
    "Negative Flag": 2, "Raster Interrupt": 5, "IRQ": 4,
    "NMI": 3, "Sprite": 4, "Sprite Pointer": 3,
    "Memory Map": 4, "Screen Memory": 3, "Character ROM": 3,
    "Color RAM": 3, "Bitmap": 3, "Bitmap Mode": 3,
    "Multicolor Mode": 3, "Hi-res Mode": 2, "Text Mode": 3,
    "Extended Color Mode": 2, "Scrolling": 3, "Collision": 2,
    "Sprite Collision": 3, "Raster": 4, "Bad Line": 2,
    "Display Enable": 2, "Interrupt": 4, "BRK": 3,
    "RTI": 3, "RTS": 4, "JSR": 4, "JMP": 4,
    "LDA": 5, "STA": 5, "LDX": 4, "STX": 4,
    "LDY": 4, "STY": 4, "TAX": 3, "TAY": 3,
    "TXA": 3, "TYA": 3, "ADC": 4, "SBC": 4,
    "AND": 3, "ORA": 3, "EOR": 3, "CMP": 3,
    "CPX": 2, "CPY": 2, "INC": 4, "DEC": 4,
    "INX": 3, "INY": 3, "DEX": 3, "DEY": 3,
    "ASL": 3, "LSR": 3, "ROL": 3, "ROR": 3,
    "PHA": 3, "PLA": 3, "PHP": 2, "PLP": 2,
    "BCC": 3, "BCS": 3, "BEQ": 3, "BNE": 3,
    "BMI": 2, "BPL": 2, "BVC": 2, "BVS": 2,
    "CLC": 3, "SEC": 3, "CLD": 2, "SED": 2,
    "CLI": 2, "SEI": 2, "CLV": 2, "NOP": 2,
    "PRINT": 4, "POKE": 5, "PEEK": 4, "SYS": 4,
    "GOTO": 3, "GOSUB": 3, "RETURN": 3, "FOR": 3,
    "NEXT": 3, "IF": 4, "THEN": 3, "DIM": 3,
    "DATA": 2, "READ": 2, "OPEN": 2, "CLOSE": 2,
    "LOAD": 3, "SAVE": 3, "VERIFY": 2, "INPUT": 3,
    "GET": 3, "REM": 2, "END": 2, "STOP": 2,
    "WAIT": 2, "POKE raster": 3, "SETTING raster": 3,
}


def render_tag_cloud(query=""):
    filtered = {
        t: w for t, w in TECHNICAL_TERMS.items()
        if not query or query.lower() in t.lower()
    }
    if not filtered:
        return "<p style='color:#888'>Nessun termine corrisponde.</p>"
    items = sorted(filtered.items(), key=lambda x: -x[1])
    html_parts = [
        "<div style='display:flex;flex-wrap:wrap;gap:6px;align-items:center;"
        "padding:8px;border:1px solid #444;border-radius:8px;background:#1a1a2e;min-height:100px'>"
    ]
    sizes = {1: 12, 2: 14, 3: 17, 4: 21, 5: 26}
    for term, weight in items:
        fs = sizes.get(weight, 14)
        color = f"hsl({max(200, 260 - weight * 20)}, 70%, {55 + weight * 4}%)"
        html_parts.append(
            f"<span onclick='pickTechTerm(\"{term}\")' "
            f"style='font-size:{fs}px;color:{color};cursor:pointer;padding:3px 6px;"
            f"border-radius:4px;transition:all .2s;user-select:none' "
            f"onmouseover='this.style.background=\"rgba(255,255,255,0.15)\"' "
            f"onmouseout='this.style.background=\"transparent\"'>{term}</span>"
        )
    html_parts.append("</div>")
    html_parts.append(
        "<script>"
        "function pickTechTerm(t){"
        "var e=document.querySelector('#tech-term-picker input,#tech-term-picker textarea');"
        "if(!e)return;"
        "var n=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set||"
        "Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value').set;"
        "n.call(e,t);"
        "e.dispatchEvent(new Event('input',{bubbles:true}));"
        "e.dispatchEvent(new Event('change',{bubbles:true}));"
        "var b=document.querySelector('#tech-term-apply');"
        "if(b)b.querySelector('button').click();"
        "}"
        "</script>"
    )
    return "\n".join(html_parts)


def launch_ui():
    lora = os.environ.get("LORA_PATH")
    gguf = os.environ.get("GGUF_MODEL_PATH")

    agent = C64CodingAgent(lora_path=lora, gguf_path=gguf)
    pm = agent.pm

    prompt_library = pm.get_config("ui.prompt_library")
    if not isinstance(prompt_library, list):
        prompt_library = [
            "Come posso cambiare il colore del bordo?",
            "Esegui un ciclo in BASIC..."
        ]

    with gr.Blocks(title="C64 Coding Agent PRO") as demo:
        with gr.Tab("Chat"):
            gr.Markdown("# C64 Coding Agent PRO")
            gr.Markdown("Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato.")

            with gr.Row():
                with gr.Column(scale=4):
                    chat_interface = gr.ChatInterface(
                        agent.chat_wrapper,
                        additional_inputs=[
                            gr.Checkbox(label="Usa Knowledge Base (RAG)", value=True),
                            gr.Checkbox(label="Auto-elabora link (aggiungi siti + pipeline)", value=False),
                            gr.Slider(
                                minimum=1,
                                maximum=5,
                                value=pm.get_config("agent.max_attempts", 3),
                                step=1,
                                label="Tentativi Self-Healing"
                            )
                        ]
                    )
                with gr.Column(scale=1):
                    gr.Markdown("### Prompt Library")
                    lib_dropdown = gr.Dropdown(choices=prompt_library, label="Snippet Comuni")
                    lib_button = gr.Button("Usa Prompt")

                    gr.Markdown("### Technical Terms")
                    term_search = gr.Textbox(
                        label="Cerca", placeholder="Filtra termini...", scale=1
                    )
                    tag_cloud = gr.HTML(render_tag_cloud())

                    selected_term = gr.Textbox(visible=False, elem_id="tech-term-picker")
                    apply_term = gr.Button("Apply", visible=False, elem_id="tech-term-apply")

                    term_search.change(
                        fn=render_tag_cloud, inputs=term_search, outputs=tag_cloud
                    )
                    apply_term.click(
                        fn=lambda x: x, inputs=selected_term,
                        outputs=chat_interface.textbox
                    )

            def fill_prompt(choice):
                return choice

            lib_button.click(fn=fill_prompt, inputs=lib_dropdown, outputs=chat_interface.textbox)

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
                    yield log_msg("ANNULLATO"); break
                yield log_msg(f"Scraping: {s}")
                yield from run_cmd_gen(f"python pipeline/c64_asm_scraper.py --sites {s} --delay 1.5")

            for s in custom_sel:
                if CTRL.cancelled:
                    yield log_msg("ANNULLATO"); break
                yield log_msg(f"Scraping: {s['name']}")
                yield log_msg("  Cerco PDF...")
                yield from run_cmd_gen(f'python pipeline/scrape_docs.py "{s["url"]}"')
                if CTRL.cancelled:
                    yield log_msg("ANNULLATO"); break
                yield log_msg("  Cerco codice Assembly...")
                yield from run_cmd_gen(f'python pipeline/scrape_url.py "{s["url"]}" "{s["name"]}"')

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
                        yield from run_cmd_gen(f"python pipeline/pdf2text.py \"{pdf_path}\" \"{tmp}\"")
                        if os.path.exists(tmp):
                            with open(tmp) as f:
                                combined.append(f.read())
                            os.remove(tmp)
                    with open("data/output/raw.txt", "w") as f:
                        f.write("\n\n".join(combined))
                    yield log_msg(f"  Uniti {len(pdfs)} PDF in data/output/raw.txt")
                    yield log_msg("Pulizia testo...")
                    yield from run_cmd_gen("python pipeline/text_cleaner.py data/output/raw.txt data/output/clean.txt")
                    yield log_msg("Generazione dataset...")
                    yield from run_cmd_gen("python pipeline/build_dataset.py data data/output/dataset_unified.jsonl")
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
                        download_btn = gr.Button("Scarica URL", variant="primary", size="sm")

                    gr.Markdown("## Scrapa Siti")
                    site_list = gr.CheckboxGroup(
                        choices=all_site_choices(),
                        label="Seleziona siti da scrapare",
                        value=[],
                    )
                    with gr.Row():
                        scrape_btn = gr.Button("Scrapa Selezionati", variant="primary", size="sm")

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
                                yield log_msg("ANNULLATO"); break
                        if not CTRL.cancelled:
                            yield log_msg("COMPLETATO")
                        CTRL.running = False

                    def on_scrape_only(sites):
                        for msg in on_scrape_batch(sites):
                            yield msg

                    download_btn.click(
                        fn=on_download_only,
                        inputs=url_input,
                        outputs=main_log
                    )
                    scrape_btn.click(
                        fn=on_scrape_only,
                        inputs=site_list,
                        outputs=main_log
                    )
                    pause_btn.click(fn=CTRL.pause, outputs=[], queue=False)
                    resume_btn.click(fn=CTRL.resume, outputs=[], queue=False)
                    cancel_btn.click(fn=CTRL.cancel, outputs=[], queue=False)

                with gr.Column(scale=1):
                    gr.Markdown("### Gestione siti")
                    new_name = gr.Textbox(label="Nome", placeholder="es. mio-sito-c64")
                    new_url = gr.Textbox(label="URL", placeholder="https://nuovo-sito-c64.it/")
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
                            return "Inserisci nome e URL.", gr.CheckboxGroup(choices=all_site_choices())
                        save_custom_site(name.strip(), url.strip())
                        return f"Sito '{name}' aggiunto!", gr.CheckboxGroup(choices=all_site_choices())

                    def on_del_site(name):
                        if not name:
                            return "Seleziona un sito da rimuovere.", gr.Dropdown(choices=[s["name"] for s in load_custom_sites()]), gr.CheckboxGroup(choices=all_site_choices())
                        remove_custom_site(name)
                        remaining = [s["name"] for s in load_custom_sites()]
                        return f"Sito '{name}' rimosso!", gr.Dropdown(choices=remaining), gr.CheckboxGroup(choices=all_site_choices())

                    add_btn.click(
                        fn=on_add_site,
                        inputs=[new_name, new_url],
                        outputs=[add_msg, site_list]
                    )
                    del_btn.click(
                        fn=on_del_site,
                        inputs=del_dropdown,
                        outputs=[del_msg, del_dropdown, site_list]
                    )

        with gr.Tab("Knowledge Base"):
            gr.Markdown("## Knowledge Base")
            kb_log = gr.Textbox(label="", lines=16)

            with gr.Row():
                with gr.Column(scale=1):
                    rebuild_btn = gr.Button("Ricostruisci Indice KB", variant="primary")
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
                        dataset_btn = gr.Button("Visualizza Dataset", variant="primary", min_width=160)
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
                        outputs=[ds_output, dataset_page, dataset_query]
                    )
                    prev_btn.click(
                        fn=lambda p, q: on_view_dataset(int(p or 0) - 1, q),
                        inputs=[dataset_page, dataset_query],
                        outputs=[ds_output, dataset_page, dataset_query]
                    )
                    next_btn.click(
                        fn=lambda p, q: on_view_dataset(int(p or 0) + 1, q),
                        inputs=[dataset_page, dataset_query],
                        outputs=[ds_output, dataset_page, dataset_query]
                    )
                    ds_search_btn.click(
                        fn=lambda q: on_view_dataset(0, q),
                        inputs=ds_search,
                        outputs=[ds_output, dataset_page, dataset_query]
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### Statistiche")
                    info_log = gr.Textbox(label="", lines=16)
                    status_btn = gr.Button("Aggiorna")
                    status_btn.click(fn=on_status, outputs=info_log)

    demo.launch(server_name="0.0.0.0", theme=gr.themes.Soft())

if __name__ == "__main__":
    launch_ui()

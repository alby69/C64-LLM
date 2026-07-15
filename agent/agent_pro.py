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
        base_model_name=None,
        lora_path=None,
        gguf_path=None,
    ):
        self.pm = PromptManager()
        backend_type = self.pm.config.get("model", {}).get("backend", "nanoGPT")

        if backend_type == "nanoGPT":
            from agent.model_backend import NanoGPTBackend
            nano_cfg = self.pm.config.get("model", {}).get("nanoGPT", {})
            model_path = nano_cfg.get("model_path", "data/models/c64-micron.pt")
            tokenizer_name = nano_cfg.get("tokenizer", "gpt2")
            print(f"Loading predefinito nanoGPT: {model_path}")
            self.backend = NanoGPTBackend(model_path, tokenizer_name)
            self.tokenizer = self.backend.tokenizer
        elif gguf_path and os.path.exists(gguf_path):
            print(f"Loading GGUF model for CPU: {gguf_path}")
            self.backend = LlamaCppBackend(gguf_path)
            self.tokenizer = None
        else:
            base_model_name = base_model_name or self.pm.config.get("agent", {}).get("model_name", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
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
                self.backend = LlamaCppBackend(gguf_path or self.pm.config.get("model", {}).get("gguf", {}).get("path"))
                self.tokenizer = None

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

    dest = "data/input"
    os.makedirs(dest, exist_ok=True)

    if is_gdrive:
        yield log_msg("La scansione e il download da Google Drive sono delegati a C64-Scrapy.")
        yield log_msg("Usa la scheda 'Integrazione C64-KB-Agent' per avviare lo spider corrispondente.")
        CTRL.running = False
        return

    elif is_archive:
        yield log_msg("La scansione e il download da Archive.org sono delegati a C64-Scrapy.")
        yield log_msg("Usa la scheda 'Integrazione C64-KB-Agent' per avviare lo spider corrispondente.")
        CTRL.running = False
        return

    elif is_pdf:
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
        yield log_msg("L'estrazione e la decodifica di file D64 sono ora delegate a PYC64.")

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
        yield log_msg("L'estrazione e la decodifica di file G64 sono ora delegate a PYC64.")

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
        yield log_msg("L'estrazione e la decodifica di file PRG sono ora delegate a PYC64.")

    else:
        yield log_msg("Il crawling e lo scraping dei siti web sono delegati a C64-Scrapy e C64-KB-Agent.")
        yield log_msg("Usa la scheda 'Integrazione C64-KB-Agent' per avviare gli spider e sincronizzare i risultati.")
        CTRL.running = False
        return

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


def render_wiki_graph_svg(selected_node=None):
    import networkx as nx
    import json as _json
    graph = load_wiki_graph()
    raw_nodes = graph.get("nodes", [])
    raw_edges = graph.get("edges", [])

    colors = {"chip": "#ff6b6b", "software": "#4ecdc4", "concetto": "#45b7d1",
              "registro": "#ffa726", "opcode": "#ab47bc", "basic": "#66bb6a"}

    node_map = {n["id"]: n for n in raw_nodes}
    G = nx.Graph()
    for n in raw_nodes:
        G.add_node(n["id"])
    for e in raw_edges:
        G.add_edge(e["from"], e["to"])

    if len(raw_nodes) == 0:
        return "<p style='color:#888'>Nessun nodo nel grafo.</p>"

    pos = nx.kamada_kawai_layout(G)

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    rx, ry = maxx - minx, maxy - miny
    if rx == 0:
        rx = 1
    if ry == 0:
        ry = 1
    W, H = 960, 640
    margin = 80
    s = min((W - 2 * margin) / rx, (H - 2 * margin) / ry) * 0.9
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2

    def to_svg_coord(x, y):
        return (W / 2 + (x - cx) * s, H / 2 + (y - cy) * s)

    node_data = []
    seen_ids = {}
    for nid in pos:
        if nid in seen_ids:
            continue
        seen_ids[nid] = True
        x, y = pos[nid]
        node = node_map.get(nid, {})
        cat = node.get("category", "concetto")
        sx, sy = to_svg_coord(x, y)
        node_data.append({
            "id": nid, "label": node.get("label", nid),
            "cat": cat, "desc": node.get("description", ""),
            "x": round(sx, 1), "y": round(sy, 1),
            "color": colors.get(cat, "#888"),
        })
    edge_data = []
    for e in raw_edges:
        if e["from"] in pos and e["to"] in pos:
            edge_data.append({"from": e["from"], "to": e["to"], "label": e.get("label", "")})

    node_by_id = {n["id"]: n for n in node_data}

    # ─── Gruppi multilivello ─────────────────────────────────────────
    GROUPS = [
        {"id": "group:opcode", "label": "Opcode 6502", "category": "opcode",
         "desc": "Opcode 6502: Operation Code per Assembly 6502. I 30 codici operativi del processore 6502/6510 con i relativi modi di indirizzamento. Doppio click per esplodere i singoli comandi.",
         "members": ["adc","sbc","lda","sta","ldx","stx","jsr","rts","jmp",
                     "bne","beq","inc","dec","inx","dex","cmp","clc","sec",
                     "sei","cli","nop","pha","pla","asl","lsr","ror","rol","and","ora","eor"]},
        {"id": "group:chip", "label": "Chip C64", "category": "chip",
         "desc": "Chip C64: i principali integrati del Commodore 64. CPU 6510 (processore), VIC-II (video), SID (audio), CIA (I/O e timer). Doppio click per esplodere.",
         "members": ["vic-ii","sid","cia","cpu-6510"]},
        {"id": "group:reg-vic", "label": "Reg. VIC-II", "category": "registro",
         "desc": "Registri VIC-II: i 15 registri di controllo del chip video ($D000-$D03F). Colore bordo/sfondo, sprite, raster interrupt, scorrimento e modalita video. Doppio click per esplodere.",
         "members": ["$D020","$D021","$D022","$D023","$D024","$D011","$D012",
                     "$D01A","$D019","$D01E","$D01F","$D01D","$D017","$D015","$D010"]},
        {"id": "group:reg-sid", "label": "Reg. SID", "category": "registro",
         "desc": "Registri SID: i registri del chip audio ($D400-$D418). Frequenza oscillatore, controllo forma d'onda, inviluppo ADSR e filtro. Doppio click per esplodere.",
         "members": ["$D400","$D404","$D405","$D406","$D418"]},
        {"id": "group:reg-cia", "label": "Reg. CIA", "category": "registro",
         "desc": "Registri CIA: i registri dei chip di I/O ($DC00-$DDFF). Porte parallele, joystick, scansione tastiera, timer e bank switching VIC-II. Doppio click per esplodere.",
         "members": ["$DC00","$DC01","$DD00"]},
        {"id": "group:reg-kernal", "label": "Vett. KERNAL", "category": "registro",
         "desc": "Vettori KERNAL: i punti di ingresso del sistema operativo in ROM ($FF81-$FFF3). CHROUT (output), GETIN (input), PLOT (cursore), init editor. Doppio click per esplodere.",
         "members": ["$FFD2","$FFE4","$FFCF","$FF81","$0314"]},
        {"id": "group:basic", "label": "Comandi BASIC", "category": "basic",
         "desc": "Comandi BASIC V2: i principali comandi del linguaggio BASIC del C64. POKE (scrittura memoria), PEEK (lettura), SYS (codice macchina), PRINT (output schermo). Doppio click per esplodere.",
         "members": ["poke","peek","sys","print"]},
    ]

    # Mappa: node_id → group_id
    node_group = {}
    for g in GROUPS:
        for mid in g["members"]:
            node_group[mid] = g["id"]

    # Posizione di ogni gruppo (centroide dei membri)
    group_pos = {}
    for g in GROUPS:
        mids = [m for m in g["members"] if m in pos]
        if not mids:
            continue
        gx = sum(pos[m][0] for m in mids) / len(mids)
        gy = sum(pos[m][1] for m in mids) / len(mids)
        sx, sy = to_svg_coord(gx, gy)
        group_pos[g["id"]] = (round(sx, 1), round(sy, 1))

    # Evita sovrapposizione tra gruppi (repulsione semplice)
    MIN_GROUP_DIST = 75
    for _ in range(30):
        moved = False
        keys = list(group_pos.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                gid1, gid2 = keys[i], keys[j]
                x1, y1 = group_pos[gid1]
                x2, y2 = group_pos[gid2]
                dx, dy = x1 - x2, y1 - y2
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < MIN_GROUP_DIST and dist > 1:
                    push = (MIN_GROUP_DIST - dist) / 2
                    nxv, nyv = dx / dist * push, dy / dist * push
                    group_pos[gid1] = (round(x1 + nxv, 1), round(y1 + nyv, 1))
                    group_pos[gid2] = (round(x2 - nxv, 1), round(y2 - nyv, 1))
                    moved = True
        if not moved:
            break

    # Costruisce edge proxy per ogni gruppo (collassato → esterno, deduplicati)
    proxy_edges = {g["id"]: set() for g in GROUPS}
    for ed in edge_data:
        fg = node_group.get(ed["from"])
        tg = node_group.get(ed["to"])
        if fg and not tg and ed["to"] in node_by_id:
            proxy_edges[fg].add(ed["to"])
        elif tg and not fg and ed["from"] in node_by_id:
            proxy_edges[tg].add(ed["from"])

    node_json = _json.dumps(node_data, ensure_ascii=False)
    groups_json = _json.dumps(GROUPS, ensure_ascii=False)
    edges_json = _json.dumps(edge_data, ensure_ascii=False)

    # ─── Generazione SVG ──────────────────────────────────────────────
    html_parts = []
    html_parts.append('<div id="wiki-pan">')
    html_parts.append(f'<svg id="wikigrafosvg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" tabindex="0" style="cursor:grab;background:#1a1a2e;border-radius:8px;outline:none">')
    html_parts.append(f'<rect width="{W}" height="{H}" fill="#1a1a2e" rx="8"/>')
    html_parts.append(f'<g id="wiki-viewport" transform="translate(0,0) scale(1)">')

    # ── Edges tra nodi individuati (nascosti se coinvolgono membri di gruppi collassati) ──
    for ed in edge_data:
        f = node_by_id.get(ed["from"])
        t = node_by_id.get(ed["to"])
        if not f or not t:
            continue
        fg = node_group.get(ed["from"])
        tg = node_group.get(ed["to"])
        hidden = " wikig-edge-hidden" if (fg or tg) else ""
        html_parts.append(
            f'<line class="wikig-edge{hidden}" x1="{f["x"]}" y1="{f["y"]}" '
            f'x2="{t["x"]}" y2="{t["y"]}" stroke="#555" stroke-width="1.5" data-f="{ed["from"]}" data-t="{ed["to"]}"/>'
        )
        # Rimuovo etichette dagli archi — saranno mostrate nella mappa connessioni sotto la descrizione

    # ── Proxy edges (gruppo → esterno, visibili quando il gruppo è collassato) ──
    for g in GROUPS:
        gid = g["id"]
        if gid not in group_pos:
            continue
        gx, gy = group_pos[gid]
        ext_ids = set(proxy_edges[gid])
        for ext_id in ext_ids:
            ext = node_by_id.get(ext_id)
            if not ext:
                continue
            html_parts.append(
                f'<line class="wikig-proxy" data-group="{gid}" x1="{gx}" y1="{gy}" '
                f'x2="{ext["x"]}" y2="{ext["y"]}" stroke="#666" stroke-width="1" stroke-dasharray="4,3"/>'
            )

    # ── Nodi gruppo (pillole arrotondate, visibili per default) ──
    # Inline onclick/ondblclick: funzionano con innerHTML (a differenza di <script>)
    for g in GROUPS:
        gid = g["id"]
        if gid not in group_pos:
            continue
        gx, gy = group_pos[gid]
        col = colors.get(g["category"], "#888")
        member_count = len([m for m in g["members"] if m in pos])
        html_parts.append(
            f'<g class="wikig-gnode" data-id="{gid}" data-group="{gid}" '
            f'onclick="onGroupClick(\'{gid}\')" style="cursor:pointer">'
            f'style="cursor:pointer">'
            f'<rect x="{gx-55}" y="{gy-14}" width="110" height="28" rx="14" '
            f'fill="{col}" fill-opacity="0.15" stroke="{col}" stroke-width="2" stroke-dasharray="5,3"/>'
            f'<text x="{gx}" y="{gy+4}" fill="#eee" font-size="11" '
            f'text-anchor="middle" font-weight="bold" font-family="monospace">{g["label"]}</text>'
            f'<text x="{gx}" y="{gy+18}" fill="#888" font-size="8" '
            f'text-anchor="middle" font-family="monospace">{member_count} membri</text></g>'
        )

    # ── Nodi membri (nascosti per default) ──
    for nd in node_data:
        gid = node_group.get(nd["id"])
        if not gid:
            continue
        r = 7 if nd["cat"] != "chip" else 10
        html_parts.append(
            f'<g class="wikig-member" data-id="{nd["id"]}" '
            f'data-group="{gid}" style="cursor:pointer;display:none">'
            f'<circle cx="{nd["x"]}" cy="{nd["y"]}" r="{r}" fill="{nd["color"]}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{nd["x"]}" y="{nd["y"]+r+10}" fill="#eee" font-size="9" '
            f'text-anchor="middle" font-family="monospace">{nd["label"]}</text></g>'
        )

    # ── Nodi liberi (non raggruppati, sempre visibili) ──
    for nd in node_data:
        if nd["id"] in node_group:
            continue
        r = 7 if nd["cat"] != "chip" else 10
        html_parts.append(
            f'<g class="wikig-node" data-id="{nd["id"]}" style="cursor:pointer">'
            f'<circle cx="{nd["x"]}" cy="{nd["y"]}" r="{r}" fill="{nd["color"]}" stroke="#fff" stroke-width="1.5"/>'
            f'<text x="{nd["x"]}" y="{nd["y"]+r+10}" fill="#eee" font-size="9" '
            f'text-anchor="middle" font-family="monospace">{nd["label"]}</text></g>'
        )

    # ── Legenda ──
    leg_x = 10
    leg_y = H - 30
    for cat, col in colors.items():
        html_parts.append(f'<circle cx="{leg_x}" cy="{leg_y}" r="5" fill="{col}"/>')
        html_parts.append(f'<text x="{leg_x+10}" y="{leg_y+4}" fill="#aaa" font-size="9" font-family="monospace">{cat}</text>')
        leg_x += 70

    html_parts.append('</g>')
    html_parts.append('</svg>')
    html_parts.append('</div>')

    # ── Toolbar e pannello descrizione ──
    html_parts.append(
        '<div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">'
        '<button id="wiki-btn-collapse" style="background:#2a2a4e;color:#ccc;border:1px solid #555;border-radius:6px;padding:4px 12px;cursor:pointer;font-size:12px">\u25B2 Comprimi tutti</button>'
        '<button id="wiki-btn-expand" style="background:#2a2a4e;color:#ccc;border:1px solid #555;border-radius:6px;padding:4px 12px;cursor:pointer;font-size:12px">\u25BC Espandi tutti</button>'
        '<button id="wiki-btn-reset" style="background:#2a2a4e;color:#ccc;border:1px solid #555;border-radius:6px;padding:4px 12px;cursor:pointer;font-size:12px">\u21BA Reset vista</button>'
        '<span id="wiki-status" style="color:#888;font-size:12px;line-height:28px;margin-left:4px">0 gruppi aperti</span>'
        '</div>'
    )
    html_parts.append(
        '<div id="wikidesc" style="margin-top:6px;padding:10px 12px;border:1px solid #555;border-radius:8px;background:#16213e;min-height:40px;color:#ccc;font-size:14px">'
        'Clicca un nodo per la descrizione, doppio click su gruppo per espanderlo/chiuderlo.'
        '</div>'
    )
    html_parts.append(
        '<div id="wikiconn" style="margin-top:6px;padding:10px 12px;border:1px solid #444;border-radius:8px;background:#1a1a2e;min-height:24px;color:#999;font-size:13px;display:none">'
        '<div style="font-weight:bold;color:#7eb8da;margin-bottom:6px;font-size:13px">\u2194 Collegamenti</div>'
        '<div id="wikiconn-lista"></div>'
        '</div>'
    )

    hl = ""
    if selected_node:
        sg = node_group.get(selected_node)
        if sg:
            hl = f'setTimeout(function(){{setGroupExpanded("{sg}",true);showNode("{selected_node}");}},100);'
        else:
            hl = f'setTimeout(function(){{showNode("{selected_node}");}},100);'

    # ── Dati embedded JSON ──
    html_parts.append(f'<script type="application/json" id="wiki-nodes-data">{node_json}</script>')
    html_parts.append(f'<script type="application/json" id="wiki-groups-data">{groups_json}</script>')
    html_parts.append(f'<script type="application/json" id="wiki-edges-data">{edges_json}</script>')

    # ── Bootstrap JS via <img onerror> ──
    js_code = f"""(function(){{
try {{
var NODES = JSON.parse(document.getElementById('wiki-nodes-data').textContent);
var GROUPS = JSON.parse(document.getElementById('wiki-groups-data').textContent);
var EDGES = JSON.parse(document.getElementById('wiki-edges-data').textContent);
var expanded = {{}};

// Costruisce mappa gruppo → nodi membri e viceversa
var nodeGroup = {{}};
var groupMembers = {{}};
GROUPS.forEach(function(g){{
    groupMembers[g.id] = g.members;
    g.members.forEach(function(mid){{ nodeGroup[mid] = g.id; }});
}});
// Mappa ID → label per nodi e gruppi
var nodeLabel = {{}};
NODES.forEach(function(n){{ nodeLabel[n.id] = n.label; }});
GROUPS.forEach(function(g){{ nodeLabel[g.id] = g.label; }});

function showNode(id){{
    // Gruppo? (gli ID gruppo non sono in NODES)
    var g = GROUPS.find(function(x){{return x.id==id;}});
    if(g){{
        document.getElementById('wikidesc').innerHTML =
            '<b style="color:#88ccff;font-size:16px">' + g.label + '</b> ' +
            '<span style="color:#888;font-size:10px">[gruppo ' + g.members.length + ' membri]</span><br>' +
            '<span style="color:#ddd">' + g.desc + '</span>';
        showConnections(id);
        return;
    }}
    var n = NODES.find(function(x){{return x.id==id;}});
    if(!n) return;
    document.getElementById('wikidesc').innerHTML =
        '<b style="color:#88ccff;font-size:16px">' + n.label + '</b><br>' +
        '<span style="color:#aaa;font-size:12px">' + n.cat + '</span><br>' +
        '<span style="color:#ddd">' + n.desc + '</span>';
    showConnections(id);
}}

function showConnections(id){{
    var div = document.getElementById('wikiconn');
    var lst = document.getElementById('wikiconn-lista');
    if(!div || !lst) return;
    var conns = [];
    EDGES.forEach(function(e){{
        if(e.from === id || e.to === id){{
            var other = e.from === id ? e.to : e.from;
            var dir = e.from === id ? '\u2192' : '\u2190';
            conns.push(dir + ' ' + (nodeLabel[other] || other) + (e.label ? ' <span style=\"color:#777\">[' + e.label + ']</span>' : ''));
        }}
    }});
    if(conns.length === 0){{
        div.style.display = 'none';
        return;
    }}
    lst.innerHTML = conns.join('<br>');
    div.style.display = '';
}}
window.showNode = showNode;

function toggleGroup(gid){{
    expanded[gid] = !expanded[gid];
    renderGroup(gid);
    showStatus();
}}
window.toggleGroup = toggleGroup;

function setGroupExpanded(gid, state){{
    if(expanded[gid] !== state){{
        expanded[gid] = state;
        renderGroup(gid);
        showStatus();
    }}
}}
window.setGroupExpanded = setGroupExpanded;

function collapseAll(){{
    Object.keys(expanded).forEach(function(gid){{
        if(expanded[gid]){{
            expanded[gid] = false;
            renderGroup(gid);
        }}
    }});
    showStatus();
}}
window.collapseAll = collapseAll;

function expandAll(){{
    Object.keys(expanded).forEach(function(gid){{
        if(!expanded[gid]){{
            expanded[gid] = true;
            renderGroup(gid);
        }}
    }});
    showStatus();
}}
window.expandAll = expandAll;

function showStatus(){{
    var n = Object.keys(expanded).filter(function(g){{return expanded[g];}}).length;
    var el = document.getElementById('wiki-status');
    if(el) el.textContent = n + ' gruppi aperti';
}}
window.showStatus = showStatus;

function onGroupClick(gid){{
    if(expanded[gid]){{
        toggleGroup(gid);
    }}else{{
        showNode(gid);
    }}
}}
window.onGroupClick = onGroupClick;

function resetGraph(){{
    collapseAll();
    var vp = document.getElementById('wiki-viewport');
    if(vp) vp.setAttribute('transform', 'translate(0,0) scale(1)');
    var desc = document.getElementById('wikidesc');
    if(desc) desc.innerHTML = 'Clicca un nodo per la descrizione, doppio click su gruppo per espanderlo/chiuderlo.';
    var conn = document.getElementById('wikiconn');
    if(conn) conn.style.display = 'none';
}}
window.resetGraph = resetGraph;

function renderGroup(gid){{
    var isExpanded = expanded[gid];
    var gnodes = document.querySelectorAll('.wikig-gnode[data-group="' + gid + '"]');
    var members = document.querySelectorAll('.wikig-member[data-group="' + gid + '"]');
    var proxies = document.querySelectorAll('.wikig-proxy[data-group="' + gid + '"]');

    // Edge dove f o t e un membro del gruppo
    groupMembers[gid].forEach(function(mid){{
        var q = '.wikig-edge[data-f="' + mid + '"],.wikig-edge[data-t="' + mid + '"]';
        document.querySelectorAll(q).forEach(function(el){{
            var fg = nodeGroup[el.getAttribute('data-f')];
            var tg = nodeGroup[el.getAttribute('data-t')];
            var show = isExpanded;
            if(fg && !expanded[fg]) show = false;
            if(tg && !expanded[tg]) show = false;
            el.classList.toggle('wikig-edge-hidden', !show);
        }});
    }});

    if(isExpanded){{
        gnodes.forEach(function(n){{ n.style.display = 'none'; }});
        members.forEach(function(n){{ n.style.display = ''; }});
        proxies.forEach(function(p){{ p.style.display = 'none'; }});
    }}else{{
        gnodes.forEach(function(n){{ n.style.display = ''; }});
        members.forEach(function(n){{ n.style.display = 'none'; }});
        proxies.forEach(function(p){{ p.style.display = ''; }});
    }}
}}

function attachHandlers(){{
    var svg = document.getElementById('wikigrafosvg');
    if(!svg) return;
    var vp = document.getElementById('wiki-viewport');
    if(!vp) return;
    var scale = 1, tx = 0, ty = 0;
    var dragging = false, lastX, lastY, dragFired = false;

    function upd() {{
        vp.setAttribute('transform', 'translate(' + tx.toFixed(1) + ',' + ty.toFixed(1) + ') scale(' + scale.toFixed(4) + ')');
    }}

    function svgX(clientX) {{
        var r = svg.getBoundingClientRect();
        return (clientX - r.left) / r.width * 960;
    }}

    function svgY(clientY) {{
        var r = svg.getBoundingClientRect();
        return (clientY - r.top) / r.height * 640;
    }}

    svg.addEventListener('wheel', function(e) {{
        e.preventDefault();
        var mx = svgX(e.clientX), my = svgY(e.clientY);
        var f = e.deltaY > 0 ? 1 / 1.1 : 1.1;
        var ns = scale * f;
        // Centra lo zoom sulla posizione del mouse
        tx = mx - (mx - tx) * (ns / scale);
        ty = my - (my - ty) * (ns / scale);
        scale = ns;
        upd();
    }}, {{ passive: false }});

    svg.addEventListener('mousedown', function(e) {{
        if(e.button !== 0) return;
        dragging = true; dragFired = false; lastX = e.clientX; lastY = e.clientY;
        svg.style.cursor = 'grabbing';
    }});

    window.addEventListener('mousemove', function(e) {{
        if(!dragging) return;
        var px = e.clientX - lastX, py = e.clientY - lastY;
        if(px*px + py*py > 9) dragFired = true;
        var r = svg.getBoundingClientRect();
        tx += px / r.width * 960;
        ty += py / r.height * 640;
        lastX = e.clientX; lastY = e.clientY;
        upd();
    }});

    window.addEventListener('mouseup', function() {{
        if(dragging) {{ dragging = false; svg.style.cursor = 'grab'; }}
    }});

    svg.addEventListener('click', function(e) {{
        if(dragFired) return;
        var t = e.target;
        while(t && !t.getAttribute('data-id')) t = t.parentNode;
        if(t && t.getAttribute('data-id')) showNode(t.getAttribute('data-id'));
    }});

    svg.addEventListener('dblclick', function(e) {{
        var t = e.target;
        while(t && !t.getAttribute('data-group')) t = t.parentNode;
        if(t) toggleGroup(t.getAttribute('data-group'));
    }});
}}

function bindToolbar(){{
    var b = document.getElementById('wiki-btn-collapse');
    if(b && !b._bound) {{ b.addEventListener('click', collapseAll); b._bound = true; }}
    b = document.getElementById('wiki-btn-expand');
    if(b && !b._bound) {{ b.addEventListener('click', expandAll); b._bound = true; }}
    b = document.getElementById('wiki-btn-reset');
    if(b && !b._bound) {{ b.addEventListener('click', resetGraph); b._bound = true; }}
}}

bindToolbar();
attachHandlers();
showStatus();
{hl}

var pan = document.getElementById('wiki-pan');
if(pan) {{
    var obs = new MutationObserver(function() {{ setTimeout(function(){{
        attachHandlers(); bindToolbar(); showStatus();
    }}, 50); }});
    obs.observe(pan, {{ childList: true, subtree: true }});
}}
}}catch(e){{console.error('WikiGraph:',e);}}
}})();"""

    import html as _html
    escaped = _html.escape(js_code, quote=True)
    html_parts.append(f'<img src="x" style="display:none" onerror="{escaped}">')

    return "\n".join(html_parts)


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

        def on_kb_sync():
            CTRL.reset()
            CTRL.start_time = time.time()
            CTRL.running = True
            yield log_msg("Avvio sincronizzazione dei dati da C64-KB-Agent...")
            try:
                from pipeline.acquisition.scrapy_kb_adapter import ScrapyKBAdapter
                adapter = ScrapyKBAdapter()
                res = adapter.sync()
                if res["status"] == "ok":
                    yield log_msg(
                        f"Sincronizzazione completata!\n"
                        f"  - File Ingeriti/Aggiornati: {res['synced']} (Nuovi: {res['new']}, Aggiornati: {res['updated']})\n"
                        f"  - File Invariati: {res['unchanged']}"
                    )
                else:
                    yield log_msg(f"Errore durante la sincronizzazione: {res['message']}")
            except Exception as e:
                yield log_msg(f"Errore: {e}")
            CTRL.running = False

        def on_run_spider(spider_name):
            if not spider_name:
                yield "Seleziona uno spider."
                return
            CTRL.reset()
            CTRL.start_time = time.time()
            CTRL.running = True
            yield log_msg(f"Avvio dello spider C64-Scrapy '{spider_name}'...")
            try:
                from pipeline.acquisition.scrapy_kb_adapter import ScrapyKBAdapter
                adapter = ScrapyKBAdapter()
                res = adapter.run_scrapy_spider(spider_name)
                if res["status"] == "ok":
                    yield log_msg(f"Spider completato con successo!")
                    yield log_msg(f"Sorgente:\n{res['spider_stdout']}")
                    sync_res = res.get("sync_result", {})
                    if sync_res:
                        yield log_msg(
                            f"Sincronizzazione post-spider completata:\n"
                            f"  - File Sincronizzati: {sync_res.get('synced', 0)}\n"
                            f"  - File Invariati: {sync_res.get('unchanged', 0)}"
                        )
                else:
                    yield log_msg(f"Errore esecuzione spider: {res['message']}")
                    if "details" in res:
                        yield log_msg(f"Dettagli:\n{res['details']}")
            except Exception as e:
                yield log_msg(f"Errore: {e}")
            CTRL.running = False

        def on_kb_rebuild():
            CTRL.reset()
            CTRL.start_time = time.time()
            CTRL.running = True
            yield log_msg("Avvio ricostruzione dell'indice vettoriale FAISS...")
            try:
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                kb = C64KnowledgeBase()
                kb.build_index()
                out = sys.stdout.getvalue()
                sys.stdout = old_stdout
                yield out
                yield log_msg("Indice FAISS ricostruito con successo!")
            except Exception as e:
                yield log_msg(f"Errore: {e}")
            CTRL.running = False

        with gr.Tab("Integrazione C64-KB-Agent"):
            gr.Markdown(
                "## 🔄 Integrazione Multi-Repository (C64-Scrapy ➔ C64-KB-Agent ➔ C64-LLM)\n"
                "In linea con la filosofia Unix **KISS** e **DRY**, questo modulo delega il web crawling e scraping a "
                "**C64-Scrapy** e la standardizzazione a **C64-KB-Agent**. L'LLM gestisce la sincronizzazione locale e il RAG."
            )

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### Sincronizzazione Conoscenza")
                    sync_btn = gr.Button("🔄 Sincronizza da C64-KB-Agent", variant="primary")

                    gr.Markdown("### Avvio Spider C64-Scrapy")
                    spider_dropdown = gr.Dropdown(
                        choices=[name for name, _ in PREDEFINED],
                        value="6502org",
                        label="Seleziona spider da avviare",
                    )
                    run_spider_btn = gr.Button("🕷️ Avvia Spider", variant="secondary")

                    gr.Markdown("### Ricostruzione Indice Local RAG")
                    rebuild_index_btn = gr.Button("🛠️ Ricostruisci Indice FAISS", variant="stop")

                    main_log = gr.Textbox(label="Log Integrazione", lines=18, max_lines=40)

                    sync_btn.click(
                        fn=on_kb_sync, inputs=[], outputs=main_log
                    )
                    run_spider_btn.click(
                        fn=on_run_spider, inputs=[spider_dropdown], outputs=main_log
                    )
                    rebuild_index_btn.click(
                        fn=on_kb_rebuild, inputs=[], outputs=main_log
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### ℹ️ Stato Ecosistema")
                    gr.Markdown(
                        "**C64-KB-Agent** è definita come la **sola base di conoscenza**.\n\n"
                        "I file vengono organizzati e validati nell'Hub prima di essere importati in questo agent "
                        "tramite il `ScrapyKBAdapter`.\n\n"
                        "L'indice locale viene memorizzato in `data/db/` ed è sincronizzato per query RAG fulminee."
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

        with gr.Tab("nanoGPT"):
            gr.Markdown("## nanoGPT — Addestra un LLM C64 da zero")
            gr.Markdown(
                "Addestra un modello GPT specializzato su C64 usando [nanoGPT](https://github.com/karpathy/nanoGPT). "
                "I dati provengono dalla tua Knowledge Base e dai sorgenti raccolti."
            )

            nanogpt_status = gr.Textbox(label="Stato", value="Pronto", interactive=False)
            nanogpt_log = gr.Textbox(label="Log / Loss Curve", lines=15, max_lines=30, interactive=False)

            with gr.Row():
                nanogpt_prepare_btn = gr.Button("Prepara Corpus", variant="secondary")
                nanogpt_start_btn = gr.Button("Avvia Training", variant="primary")
                nanogpt_stop_btn = gr.Button("Stop", variant="stop")

            with gr.Row():
                nanogpt_model_size = gr.Radio(
                    ["124M (micro)", "350M (base)"],
                    label="Dimensione modello",
                    value="124M (micro)",
                )
                nanogpt_init = gr.Radio(
                    ["scratch", "gpt2", "gpt2-medium", "resume"],
                    label="Inizializzazione",
                    value="scratch",
                )

            with gr.Row():
                nanogpt_lr = gr.Number(label="Learning rate", value=6e-4, minimum=1e-6, maximum=1e-2, step=1e-5)
                nanogpt_max_iters = gr.Number(label="Max iterazioni", value=10000, minimum=100, maximum=100000, step=100)
                nanogpt_batch_size = gr.Number(label="Batch size", value=12, minimum=1, maximum=128, step=1)
                nanogpt_block_size = gr.Number(label="Block size (contesto)", value=1024, minimum=128, maximum=2048, step=128)

            def on_nanogpt_prepare():
                from pipeline.nanogpt_prepper import NanoGPTPrepper
                prepper = NanoGPTPrepper()
                ok = prepper.prepare(tokenization_mode="gpt2")
                return "Pronto" if ok else "Errore"

            def on_nanogpt_train(model_size, init, lr, max_iters, batch_size, block_size):
                CTRL.reset()
                CTRL.start_time = time.time()
                CTRL.running = True

                size_map = {"124M (micro)": "124M", "350M (base)": "350M"}
                model_sz = size_map.get(model_size, "124M")

                from pipeline.nanogpt_trainer import NanoGPTTrainer
                trainer = NanoGPTTrainer()
                if not trainer.ensure_repo():
                    yield log_msg("Errore: impossibile clonare nanoGPT")
                    return
                trainer.link_data()
                trainer.write_config(
                    model_size=model_sz,
                    init_from=init,
                    batch_size=int(batch_size),
                    block_size=int(block_size),
                    lr=float(lr),
                    max_iters=int(max_iters),
                )

                cmd = f"python pipeline/nanogpt_trainer.py --model-size {model_sz} --init-from {init} --batch-size {int(batch_size)} --block-size {int(block_size)} --lr {float(lr)} --max-iters {int(max_iters)}"
                yield log_msg("Avvio training nanoGPT...")
                for msg in run_cmd_gen(cmd):
                    yield msg
                    if CTRL.cancelled:
                        break

                if not CTRL.cancelled:
                    yield log_msg("✅ Training nanoGPT completato!")
                    # Auto-conversione in GGUF
                    trainer.convert_to_gguf()
                else:
                    yield log_msg("🛑 Training terminato manuale.")

                CTRL.running = False

            def on_nanogpt_stop():
                CTRL.cancel()
                return "Training interrotto manualmente."

            nanogpt_prepare_btn.click(
                fn=on_nanogpt_prepare,
                outputs=[nanogpt_status],
            )
            nanogpt_start_btn.click(
                fn=on_nanogpt_train,
                inputs=[nanogpt_model_size, nanogpt_init, nanogpt_lr, nanogpt_max_iters, nanogpt_batch_size, nanogpt_block_size],
                outputs=[nanogpt_log],
            )
            nanogpt_stop_btn.click(
                fn=on_nanogpt_stop,
                outputs=[nanogpt_log],
            )

        with gr.Tab("Grafo Wiki"):
            gr.Markdown("## Grafo della Conoscenza C64")
            gr.Markdown(
                "Esplora le connessioni tra chip, registri, opcode e concetti del Commodore 64. "
                "Clicca un nodo per vedere la descrizione."
            )
            wiki_graph_html = gr.HTML(render_wiki_graph_svg(), sanitize_html=False)
            wiki_search = gr.Textbox(
                label="Cerca nodo",
                placeholder="es. VIC-II, $D020, sprite...",
            )
            wiki_search.submit(
                fn=lambda q: render_wiki_graph_svg(q if q else None),
                inputs=wiki_search,
                outputs=wiki_graph_html,
            )
            wiki_reset = gr.Button("Reimposta grafo")
            wiki_reset.click(
                fn=lambda: render_wiki_graph_svg(None),
                outputs=wiki_graph_html,
            )

    demo.launch(server_name="0.0.0.0", theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_ui()

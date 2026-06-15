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
        choices.append((f"{s['name']} ({s['url']})", s["name"]))
    return choices


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

    def chat_wrapper(self, message, history, use_rag, max_attempts):
        formatted_history = []
        for user_msg, bot_msg in history:
            formatted_history.append({"role": "user", "content": user_msg})
            formatted_history.append({"role": "assistant", "content": bot_msg})

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

            return response + source_text + log_text
        except Exception as e:
            return f"Errore durante l'elaborazione: {str(e)}"


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

    if is_pdf or is_d64 or is_prg or is_g64 or is_archive:
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
            pdf_files = [f for f in files if f["name"].lower().endswith(".pdf")]

            disk_files = d64_files + g64_files + prg_files

            if disk_files:
                yield log_msg(f"Trovati {len(disk_files)} file disco/PRG. Download...")
                subdir = os.path.join(dest, item_id)
                os.makedirs(subdir, exist_ok=True)
                for df in disk_files:
                    fname = df["name"]
                    dl_url = f"https://archive.org/download/{item_id}/{fname}"
                    yield log_msg(f"  Download: {fname}")
                    r = req.get(dl_url, stream=True, timeout=60, verify=False)
                    r.raise_for_status()
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

            if pdf_files:
                yield log_msg(f"Trovati {len(pdf_files)} PDF. Download...")
                subdir = os.path.join(dest, item_id) if not disk_files else subdir
                os.makedirs(subdir, exist_ok=True)
                for pf in pdf_files[:5]:
                    fname = pf["name"]
                    dl_url = f"https://archive.org/download/{item_id}/{fname}"
                    yield log_msg(f"  Download: {fname}")
                    r = req.get(dl_url, stream=True, timeout=60, verify=False)
                    r.raise_for_status()
                    local = os.path.join(subdir, os.path.basename(fname))
                    with open(local, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)

            if not disk_files and not pdf_files:
                yield log_msg("Nessun file D64/G64/PRG/PDF trovato in questo item.")
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
        pdf_count = 0
        for root, _, files in os.walk("data/input"):
            for fname in files:
                if fname.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, fname)
                    yield log_msg(f"Elaboro: {fname}")
                    yield from run_cmd_gen(f"INPUT_PDF={pdf_path} python run_pipeline.py")
                    pdf_count += 1
                    if CTRL.cancelled:
                        return
                elif fname.lower().endswith(".d64"):
                    yield from run_cmd_gen(f"python pipeline/extract_d64.py \"{os.path.join(root, fname)}\" \"{root}\"")
                elif fname.lower().endswith(".g64"):
                    yield from run_cmd_gen(f"python pipeline/extract_g64.py \"{os.path.join(root, fname)}\" \"{root}\"")
                elif fname.lower().endswith(".prg"):
                    yield from run_cmd_gen(f"python pipeline/extract_prg.py \"{os.path.join(root, fname)}\" \"{root}\"")

        if pdf_count == 0:
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
    for directory, _ in KB_DIRS:
        candidate = os.path.join(directory, rel_path)
        if os.path.exists(candidate):
            full_path = candidate
            break
    if not full_path:
        return f"File non trovato: {rel_path}"
    try:
        with open(full_path, "r") as f:
            content = f.read()
        sz = os.path.getsize(full_path)
        lines = content.split("\n")
        preview = "\n".join(lines[:50])
        extra = f"\n\n... ({len(lines) - 50} righe in piu', {sz} byte totali)" if len(lines) > 50 else ""
        return f"--- {rel_path} ({sz} byte) ---\n\n{preview}{extra}"
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


def on_view_dataset():
    path = "data/output/dataset_unified.jsonl"
    if not os.path.exists(path):
        return "Dataset non trovato. Esegui prima la pipeline."
    with open(path) as f:
        lines = f.readlines()
    n = len(lines)
    sample = "".join(lines[:20])
    return f"Dataset: {n} entries\n\nPrime 20 righe:\n{sample}"


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
                    gr.Examples(
                        examples=["$D020", "VIC-II", "SID", "KERNAL", "Raster Interrupt"],
                        inputs=chat_interface.textbox
                    )

            def fill_prompt(choice):
                return choice

            lib_button.click(fn=fill_prompt, inputs=lib_dropdown, outputs=chat_interface.textbox)

        with gr.Tab("Scarica"):
            gr.Markdown("## Scarica e integra nella KB")
            gr.Markdown("Incolla un URL: PDF diretto, Archive.org, o sito web.")

            quick_url = gr.Textbox(
                label="URL",
                placeholder="https://...manuale.pdf  o  archive.org/details/...  o  https://sito-con-asm/",
            )

            with gr.Row():
                start_btn = gr.Button("Avvia", variant="primary", size="sm")
                pause_btn = gr.Button("Pausa", size="sm")
                resume_btn = gr.Button("Riprendi", size="sm")
                cancel_btn = gr.Button("Annulla", variant="stop", size="sm")

            quick_log = gr.Textbox(label="Log", lines=18, max_lines=40)

            start_btn.click(
                fn=lambda: CTRL.reset() or None,
                outputs=[], queue=False
            ).then(
                fn=download_and_integrate,
                inputs=quick_url,
                outputs=quick_log
            )

            pause_btn.click(fn=CTRL.pause, outputs=[], queue=False)
            resume_btn.click(fn=CTRL.resume, outputs=[], queue=False)
            cancel_btn.click(fn=CTRL.cancel, outputs=[], queue=False)

        with gr.Tab("Siti"):
            gr.Markdown("## Scraping siti Assembly C64")

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Siti predefiniti e personalizzati")
                    site_list = gr.CheckboxGroup(
                        choices=all_site_choices(),
                        label="Seleziona siti da scrapare",
                        value=["6502org", "codebase64", "c64wiki"],
                    )

                    with gr.Row():
                        scrape_btn = gr.Button("Scrapa Selezionati", variant="primary", size="sm")
                        scrape_cancel_btn = gr.Button("Annulla", variant="stop", size="sm")

                    scrape_log = gr.Textbox(label="Log", lines=15, max_lines=30)

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
                            yield from run_cmd_gen(f'python pipeline/scrape_url.py "{s["url"]}" "{s["name"]}"')

                        if not CTRL.cancelled:
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

                    scrape_btn.click(fn=on_scrape_batch, inputs=site_list, outputs=scrape_log)
                    scrape_cancel_btn.click(fn=CTRL.cancel, outputs=[], queue=False)

                with gr.Column(scale=1):
                    gr.Markdown("### Aggiungi un sito")
                    new_name = gr.Textbox(label="Nome", placeholder="es. mio-sito-c64")
                    new_url = gr.Textbox(label="URL", placeholder="https://nuovo-sito-c64.it/")
                    add_btn = gr.Button("Aggiungi alla lista")
                    add_msg = gr.Textbox(label="", lines=1)

                    def on_add_site(name, url):
                        if not name or not url:
                            return "Inserisci nome e URL.", gr.CheckboxGroup(choices=all_site_choices())
                        save_custom_site(name.strip(), url.strip())
                        return f"Sito '{name}' aggiunto!", gr.CheckboxGroup(choices=all_site_choices())

                    add_btn.click(
                        fn=on_add_site,
                        inputs=[new_name, new_url],
                        outputs=[add_msg, site_list]
                    )

        with gr.Tab("Dati"):
            gr.Markdown("## Gestione dati e manutenzione")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Knowledge Base")
                    rebuild_btn = gr.Button("Ricostruisci Indice KB", variant="primary")
                    rebuild_btn.click(fn=on_rebuild, outputs=info_log)

                    gr.Markdown("### Dataset")
                    dataset_btn = gr.Button("Visualizza Dataset")
                    dataset_btn.click(fn=on_view_dataset, outputs=info_log)

                with gr.Column(scale=1):
                    gr.Markdown("### Statistiche")
                    status_btn = gr.Button("Aggiorna")
                    status_btn.click(fn=on_status, outputs=info_log)

                with gr.Column(scale=2):
                    gr.Markdown("### Esplora file KB")
                    list_btn = gr.Button("Elenca tutti i file", size="sm")
                    file_dropdown = gr.Dropdown(
                        choices=lambda: all_kb_file_choices(),
                        label="Anteprima file",
                        allow_custom_value=True,
                    )
                    preview_btn = gr.Button("Visualizza", size="sm")

            info_log = gr.Textbox(label="", lines=16)

            list_btn.click(fn=list_kb_files, outputs=info_log)
            preview_btn.click(fn=preview_kb_file, inputs=file_dropdown, outputs=info_log)

    demo.launch(server_name="0.0.0.0", theme=gr.themes.Soft())

if __name__ == "__main__":
    launch_ui()

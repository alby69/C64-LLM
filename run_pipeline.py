import subprocess
import os
from datetime import datetime

# -----------------------------
# CONFIGURAZIONE
# -----------------------------
INPUT_PDF = os.getenv("INPUT_PDF", "data/input/manuale.pdf")
RAW_TEXT = "data/output/raw.txt"
CLEAN_TEXT = "data/output/clean.txt"
DATASET_JSONL = "data/output/dataset_unified.jsonl"
LOG_DIR = "logs"
REPORT_FILE = os.path.join(LOG_DIR, "pipeline_report.txt")

STEPS = [
    {
        "name": "Estrazione e Pulizia PDF (built-in Pure Python)",
        "cmd": f"python pipeline/process_batch.py",
        "log": os.path.join(LOG_DIR, "01_pdf_process.log"),
    },
    {
        "name": "Generazione Dataset Unificato",
        "cmd": f"python pipeline/build_dataset.py data {DATASET_JSONL}",
        "log": os.path.join(LOG_DIR, "03_dataset_gen.log"),
    },
    {
        "name": "Knowledge Distillation (opzionale — usa Teacher LLM esterno)",
        "cmd": "python pipeline/knowledge_distiller.py --generate --max-chunks 100",
        "log": os.path.join(LOG_DIR, "04_distillation.log"),
    },
    {
        "name": "Costruzione Knowledge Base",
        "cmd": "python agent/knowledge_base.py",
        "log": os.path.join(LOG_DIR, "05_kb_build.log"),
    },
]


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def run_step(step):
    print(f"[INFO] Eseguendo: {step['name']}")
    if not os.path.exists(os.path.dirname(step["log"])):
        os.makedirs(os.path.dirname(step["log"]))

    with open(step["log"], "w") as log_file:
        try:
            # For process_batch or others, we can check if data/input directory has PDFs or if INPUT_PDF exists
            if "process_batch.py" in step["cmd"]:
                if not os.path.exists("data/input") or not any(f.endswith(".pdf") for f in os.listdir("data/input")):
                    print(f"[WARN] Nessun PDF trovato in data/input. Salto questo step.")
                    return True, f"{step['name']} saltato (nessun PDF trovato)."

            result = subprocess.run(
                step["cmd"],
                shell=True,
                check=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
            return True, f"{step['name']} completato con successo."
        except subprocess.CalledProcessError as e:
            return (
                False,
                f"{step['name']} FALLITO! Errore: {e}. Controlla {step['log']}",
            )
        except Exception as e:
            return False, f"{step['name']} FALLITO! Errore inatteso: {e}"


def main():
    ensure_dir(LOG_DIR)
    ensure_dir("data/output")
    ensure_dir("data/src")

    report_lines = [f"Master Script Pipeline PRO - {datetime.now()}\n"]

    for step in STEPS:
        success, message = run_step(step)
        report_lines.append(message)
        print(message)
        if not success:
            report_lines.append("Pipeline interrotta.\n")
            break

    with open(REPORT_FILE, "w") as report:
        report.write("\n".join(report_lines))

    print(f"\n[INFO] Pipeline completata. Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()

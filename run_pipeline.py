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
        "name": "Estrazione PDF (PRO)",
        "cmd": f"python pipeline/pdf2text.py {INPUT_PDF} {RAW_TEXT}",
        "log": os.path.join(LOG_DIR, "01_pdf_extraction.log"),
    },
    {
        "name": "Pulizia Testo (PRO)",
        "cmd": f"python pipeline/text_cleaner.py {RAW_TEXT} {CLEAN_TEXT}",
        "log": os.path.join(LOG_DIR, "02_text_cleaning.log"),
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
            # Check if input file exists for PDF extraction
            if "pdf2text.py" in step["cmd"]:
                pdf_path = step["cmd"].split()[2]
                if not os.path.exists(pdf_path):
                    print(f"[WARN] PDF non trovato: {pdf_path}. Salto questo step.")
                    return True, f"{step['name']} saltato (file mancante)."

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

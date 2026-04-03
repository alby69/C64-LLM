import subprocess
import os
from datetime import datetime

# -----------------------------
# CONFIGURAZIONE
# -----------------------------
INPUT_PDF = os.getenv("INPUT_PDF", "/data/input/libro.pdf")
RAW_TEXT = os.getenv("RAW_TEXT", "/data/output/raw.txt")
CLEAN_TEXT = os.getenv("CLEAN_TEXT", "/data/output/clean.txt")
DATASET_JSONL = os.getenv("DATASET_JSONL", "/data/output/dataset.jsonl")
LOG_DIR = "logs"
REPORT_FILE = os.path.join(LOG_DIR, "report.txt")

# Lista dei comandi da eseguire in sequenza (puoi modificare i percorsi se cambiano)
STEPS = [
    {
        "name": "Estrazione PDF",
        "cmd": f"python pdf2text.py {INPUT_PDF} {RAW_TEXT}",
        "log": os.path.join(LOG_DIR, "pdf_extraction.log")
    },
    {
        "name": "Pulizia Testo",
        "cmd": f"python text_cleaner.py {RAW_TEXT} {CLEAN_TEXT}",
        "log": os.path.join(LOG_DIR, "text_cleaning.log")
    },
    {
        "name": "Creazione Dataset Hardcore",
        "cmd": f"python dataset_hardcore.py {CLEAN_TEXT} {DATASET_JSONL}",
        "log": os.path.join(LOG_DIR, "dataset_hardcore.log")
    },
    {
        "name": "Training LoRA",
        "cmd": f"python train_lora.py {DATASET_JSONL}",
        "log": os.path.join(LOG_DIR, "training_lora.log")
    },
    {
        "name": "Validazione Emulator C64",
        "cmd": "python validate_emulator.py",
        "log": os.path.join(LOG_DIR, "validate_emulator.log")
    }
]

# -----------------------------
# FUNZIONI DI SUPPORTO
# -----------------------------
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def run_step(step):
    print(f"[INFO] Eseguendo: {step['name']}")
    with open(step["log"], "w") as log_file:
        try:
            result = subprocess.run(
                step["cmd"], shell=True, check=True,
                stdout=log_file, stderr=subprocess.STDOUT
            )
            return True, f"{step['name']} completato con successo."
        except subprocess.CalledProcessError:
            return False, f"{step['name']} FALLITO! Controlla {step['log']}"

# -----------------------------
# MAIN SCRIPT
# -----------------------------
def main():
    ensure_dir(LOG_DIR)
    report_lines = [f"Master Script Pipeline - {datetime.now()}\n"]
    
    for step in STEPS:
        success, message = run_step(step)
        report_lines.append(message)
        print(message)
        if not success:
            report_lines.append("Pipeline interrotta a causa di errore.\n")
            break
    
    # Salva report finale
    with open(REPORT_FILE, "w") as report:
        report.write("\n".join(report_lines))
    
    print(f"\n[INFO] Report finale salvato in {REPORT_FILE}")

if __name__ == "__main__":
    main()
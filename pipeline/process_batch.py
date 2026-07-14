import os
import glob
import logging
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("batch_processor")

def process_all_pdfs(base_dirs, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = []
    for d in base_dirs:
        pdf_files.extend(glob.glob(f"{d}/**/*.pdf", recursive=True))

    logger.info(f"Trovati {len(pdf_files)} file PDF da elaborare.")

    for pdf_path in pdf_files:
        basename = os.path.basename(pdf_path)
        name_no_ext = os.path.splitext(basename)[0]
        output_txt = os.path.join(output_dir, name_no_ext + ".txt")
        output_clean = os.path.join(output_dir, name_no_ext + "_clean.txt")

        logger.info(f"Elaborazione in corso: {basename}...")

        if not fitz:
            logger.error("PyMuPDF (fitz) non installato. Impossibile estrarre testo dal PDF.")
            continue

        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()

            # Salva testo grezzo
            with open(output_txt, "w", encoding="utf-8") as f:
                f.write(text)

            # Semplice pulizia del testo (visto che text_cleaner.py e' rimosso/delegato)
            # Rimuove righe vuote duplicate e spazi consecutivi insoliti
            lines = [line.strip() for line in text.split("\n")]
            cleaned_lines = []
            for line in lines:
                if line:
                    cleaned_lines.append(line)
                elif cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")

            clean_text = "\n".join(cleaned_lines)
            with open(output_clean, "w", encoding="utf-8") as f:
                f.write(clean_text)

            logger.info(f"  OK: {basename}")
        except Exception as e:
            logger.error(f"  ERRORE: {basename} - {e}")

if __name__ == "__main__":
    process_all_pdfs(["data/input", "data/tmp"], "data/output")

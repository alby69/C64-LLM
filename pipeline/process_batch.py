import os
import subprocess
import glob
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("batch_processor")

def process_all_pdfs(base_dirs, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    pdf_files = []
    for d in base_dirs:
        pdf_files.extend(glob.glob(f"{d}/**/*.pdf", recursive=True))

    logger.info(f"Found {len(pdf_files)} PDF files to process.")

    for pdf_path in pdf_files:
        basename = os.path.basename(pdf_path)
        name_no_ext = os.path.splitext(basename)[0]
        output_base = os.path.join(output_dir, name_no_ext)

        logger.info(f"Processing {basename}...")

        try:
            result = subprocess.run(
                ["python3", "pipeline/pdf2marker.py", pdf_path, output_base],
                capture_output=True, text=True,
            )

            if result.returncode != 0:
                logger.warning(f"  pdf2marker fallito per {basename}, tento pdf2text fallback...")
                fallback_result = subprocess.run(
                    ["python3", "pipeline/pdf2text.py", pdf_path, output_base + ".txt"],
                    capture_output=True, text=True,
                )
                if fallback_result.returncode != 0:
                    logger.error(f"  FALLBACK FALLITO: {basename} - {fallback_result.stderr.strip()}")
                    continue

            txt_path = output_base + ".txt"
            clean_path = output_base + "_clean.txt"
            if os.path.exists(txt_path):
                subprocess.run(
                    ["python3", "pipeline/text_cleaner.py", txt_path, clean_path],
                    check=True, capture_output=True, text=True,
                )

            logger.info(f"  OK: {basename}")
        except Exception as e:
            logger.error(f"  ERROR: {basename} - {e}")

if __name__ == "__main__":
    process_all_pdfs(["data/input", "data/tmp"], "data/output")

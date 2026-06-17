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
        raw_output = os.path.join(output_dir, f"{name_no_ext}_raw.txt")
        clean_output = os.path.join(output_dir, f"{name_no_ext}_clean.txt")

        logger.info(f"Processing {basename}...")

        # 1. Extraction
        try:
            subprocess.run(["python3", "pipeline/pdf2text.py", pdf_path, raw_output], check=True)
            # 2. Cleaning
            subprocess.run(["python3", "pipeline/text_cleaner.py", raw_output, clean_output], check=True)
            logger.info(f"Successfully processed {basename}")
        except Exception as e:
            logger.error(f"Failed to process {basename}: {e}")

if __name__ == "__main__":
    process_all_pdfs(["data/input", "data/tmp"], "data/output")

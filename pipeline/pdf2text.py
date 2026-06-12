import sys
import fitz  # PyMuPDF
from pathlib import Path

def extract_text_pro(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        # Use "blocks" to preserve some structure if "layout" is not supported or fails
        text = page.get_text("blocks")
        # Convert blocks to text lines
        block_text = "\n".join([b[4] for b in text])
        full_text += block_text + "\n\f" # use form feed to separate pages
    return full_text

def main():
    if len(sys.argv) < 3:
        print("Uso: python pdf2text_pro.py input.pdf output.txt")
        return

    input_pdf = sys.argv[1]
    output_txt = sys.argv[2]

    if not Path(input_pdf).exists():
        print(f"File non trovato: {input_pdf}")
        return

    text = extract_text_pro(input_pdf)

    Path(output_txt).write_text(text, encoding="utf-8")
    print(f"Testo (PRO) estratto salvato in: {output_txt}")

if __name__ == "__main__":
    main()

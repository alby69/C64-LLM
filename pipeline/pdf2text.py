import sys
import fitz  # PyMuPDF
from pathlib import Path

def extract_text_pro(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        # Preserve layout to better identify code blocks
        text = page.get_text("layout")
        full_text += text + "\n\f" # use form feed to separate pages
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

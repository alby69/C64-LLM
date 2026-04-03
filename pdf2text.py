import sys
from pathlib import Path
from pdfminer.high_level import extract_text

def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)

def main():
    if len(sys.argv) < 3:
        print("Uso: python pdf2text.py input.pdf output.txt")
        return

    input_pdf = sys.argv[1]
    output_txt = sys.argv[2]

    text = extract_text_from_pdf(input_pdf)

    Path(output_txt).write_text(text, encoding="utf-8")
    print(f"Testo estratto salvato in: {output_txt}")

if __name__ == "__main__":
    main()
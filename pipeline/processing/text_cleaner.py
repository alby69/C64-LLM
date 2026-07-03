import re
import sys
from pathlib import Path

def advanced_clean(text):
    # Remove control chars but keep accented letters and symbols
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    # Remove standalone page numbers (e.g., "  123  " at start/end of lines)
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # Remove typical PDF headers/footers (example: "Commodore 64 Programmer's Reference Guide")
    # This is a placeholder for common strings found in manuals
    headers = [
        r"Commodore 64 Programmer's Reference Guide",
        r"C64 User's Guide",
        r"6502 Assembly Language Programming"
    ]
    for h in headers:
        text = re.sub(h, '', text, flags=re.IGNORECASE)

    # Normalize spaces but keep indentation (essential for some ASM)
    text = re.sub(r'[ \t]+', ' ', text)

    # Fix common PDF extraction errors in C64 code
    # Example: "L DA" -> "LDA", "S TA" -> "STA"
    for op in ["LDA", "STA", "LDX", "STX", "LDY", "STY", "JSR", "JMP", "RTS"]:
        pattern = r'\b' + r'\s*'.join(list(op)) + r'\b'
        text = re.sub(pattern, op, text, flags=re.IGNORECASE)

    # Normalize hex notation
    # $ C000 -> $C000
    text = re.sub(r'\$\s+([0-9A-F]{2,4})', r'$\1', text, flags=re.IGNORECASE)

    # Fix broken labels (e.g., "LABEL :" -> "LABEL:")
    text = re.sub(r'([A-Z0-9_]+)\s+:', r'\1:', text, flags=re.IGNORECASE)

    # Normalize double newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()

def main():
    if len(sys.argv) < 3:
        print("Uso: python text_cleaner_pro.py input.txt output.txt")
        return

    input_txt = sys.argv[1]
    output_txt = sys.argv[2]

    if not Path(input_txt).exists():
        print(f"File non trovato: {input_txt}")
        return

    text = Path(input_txt).read_text(encoding="utf-8")
    cleaned = advanced_clean(text)

    Path(output_txt).write_text(cleaned, encoding="utf-8")
    print(f"Testo pulito salvato in: {output_txt}")

if __name__ == "__main__":
    main()

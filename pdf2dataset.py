import os
import json
import re
from typing import List
import fitz  # PyMuPDF
from transformers import pipeline

# =========================
# CONFIG
# =========================
INPUT_FOLDER = "pdfs"
OUTPUT_FILE = "dataset_final.jsonl"

CHUNK_SIZE = 300
OVERLAP = 50
MIN_LENGTH = 80

MODEL_NAME = "microsoft/phi-2"  # leggero consigliato

# =========================
# LOAD MODEL
# =========================
print("Caricamento modello...")
generator = pipeline(
    "text-generation",
    model=MODEL_NAME,
    device_map="auto",
    max_new_tokens=200
)

# =========================
# 6502 OPCODES COMPLETI
# =========================
ASM_KEYWORDS = [
    "ADC","AND","ASL","BCC","BCS","BEQ","BIT","BMI","BNE","BPL","BRK","BVC","BVS",
    "CLC","CLD","CLI","CLV",
    "CMP","CPX","CPY",
    "DEC","DEX","DEY",
    "EOR",
    "INC","INX","INY",
    "JMP","JSR",
    "LDA","LDX","LDY",
    "LSR",
    "NOP",
    "ORA",
    "PHA","PHP","PLA","PLP",
    "ROL","ROR",
    "RTI","RTS",
    "SBC",
    "SEC","SED","SEI",
    "STA","STX","STY",
    "TAX","TAY","TSX","TXA","TXS","TYA"
]

# =========================
# PDF → TEXT
# =========================
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    return "\n".join([page.get_text() for page in doc])

# =========================
# CLEAN TEXT
# =========================
def clean_text(text: str) -> str:
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[^\x00-\x7F\$#:\.,\(\)\[\]\+\-\*/\n]', ' ', text)
    return text.strip()

# =========================
# ASM LINE DETECTION
# =========================
def looks_like_asm_line(line: str) -> bool:
    line = line.strip().upper()

    return bool(
        re.match(r'^[A-Z_][A-Z0-9_]*:', line) or     # label
        re.match(r'^\*=\$[0-9A-F]+', line) or        # origin
        re.match(r'^[A-Z]{3}\s', line)               # opcode
    )

# =========================
# EXTRACT ASM BLOCKS
# =========================
def extract_asm_blocks(text: str) -> List[str]:
    lines = text.split("\n")
    blocks = []
    current_block = []

    for line in lines:
        if looks_like_asm_line(line):
            current_block.append(line)
        else:
            if len(current_block) >= 2:
                blocks.append("\n".join(current_block))
            current_block = []

    if len(current_block) >= 2:
        blocks.append("\n".join(current_block))

    return blocks

# =========================
# NORMAL TEXT CHUNKS
# =========================
def split_into_chunks(text: str) -> List[str]:
    words = text.split()
    chunks = []

    i = 0
    while i < len(words):
        chunk = words[i:i + CHUNK_SIZE]
        chunk_text = " ".join(chunk)

        if len(chunk_text) > MIN_LENGTH:
            chunks.append(chunk_text)

        i += CHUNK_SIZE - OVERLAP

    return chunks

# =========================
# PROMPT BUILDER
# =========================
def build_prompt(text: str, is_code: bool) -> str:
    if is_code:
        return f"""
Spiega dettagliatamente questo codice assembly 6502 per Commodore 64.
Descrivi ogni istruzione e il risultato.

Codice:
{text}

Risposta:
"""
    else:
        return f"""
Spiega chiaramente questo concetto sul Commodore 64.
Includi esempi pratici se possibile.

Testo:
{text}

Risposta:
"""

# =========================
# GENERATE OUTPUT
# =========================
def generate_output(prompt: str) -> str:
    try:
        result = generator(prompt)[0]["generated_text"]
        return result.split("Risposta:")[-1].strip()
    except Exception as e:
        print("Errore:", e)
        return ""

# =========================
# PROCESS PDF
# =========================
def process_pdf(path: str) -> List[dict]:
    raw = extract_text_from_pdf(path)
    clean = clean_text(raw)

    dataset = []

    # 🔥 1. ASM BLOCKS
    asm_blocks = extract_asm_blocks(clean)

    for block in asm_blocks:
        prompt = build_prompt(block, True)
        output = generate_output(prompt)

        if len(output) < 30:
            continue

        dataset.append({
            "instruction": "Spiega codice assembly 6502",
            "input": block,
            "output": output
        })

    # 🔥 2. TESTO NORMALE
    chunks = split_into_chunks(clean)

    for chunk in chunks:
        prompt = build_prompt(chunk, False)
        output = generate_output(prompt)

        if len(output) < 30:
            continue

        dataset.append({
            "instruction": "Spiega concetto C64",
            "input": chunk,
            "output": output
        })

    return dataset

# =========================
# MAIN PROCESS
# =========================
def process_all():
    all_data = []

    for file in os.listdir(INPUT_FOLDER):
        if not file.endswith(".pdf"):
            continue

        print(f"\n📘 {file}")
        path = os.path.join(INPUT_FOLDER, file)

        data = process_pdf(path)
        all_data.extend(data)

        print(f"✔ Generati: {len(data)} esempi")

    return all_data

# =========================
# SAVE
# =========================
def save_jsonl(data: List[dict]):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for row in data:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

# =========================
# MAIN
# =========================
def main():
    dataset = process_all()

    print(f"\n🔥 Dataset totale: {len(dataset)}")

    save_jsonl(dataset)

    print("✅ Dataset pronto per training!")

if __name__ == "__main__":
    main()
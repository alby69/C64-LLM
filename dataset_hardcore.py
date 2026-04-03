import re
import json
import random
import sys
from pathlib import Path

# ----------------------------
# CONFIG
# ----------------------------

MIN_LINES = 1

INSTRUCTION_POOL = [
    "Scrivi una routine in assembly 6502",
    "Genera codice assembly per C64",
    "Implementa questa logica in 6502",
    "Scrivi codice ottimizzato per Commodore 64"
]

CONSTRAINTS_POOL = [
    "CPU 6502",
    "Ottimizzato per velocità",
    "Compatibile con memoria C64",
    "Zero page quando possibile",
    "Compatibile con BASIC SYS"
]

ASM_OPS = ["LDA", "STA", "JMP", "JSR", "LDX", "LDY", "ADC", "SBC", "RTS", "CLC", "SEC", "INC", "DEC", "AND", "ORA", "EOR", "CMP", "CPX", "CPY", "BEQ", "BNE", "BCC", "BCS", "BPL", "BMI", "BVC", "BVS", "TAX", "TAY", "TXA", "TYA", "TSX", "TXS", "PHA", "PLA", "PHP", "PLP", "BRK", "RTI", "NOP"]

def is_asm_line(line):
    stripped = line.strip().upper()
    for op in ASM_OPS:
        if stripped.startswith(op):
            return True
    return False

def detect_asm_blocks(text):
    lines = text.split('\n')
    blocks = []
    current_block = []
    
    for line in lines:
        if is_asm_line(line):
            current_block.append(line.strip())
        elif current_block:
            if len(current_block) >= MIN_LINES:
                blocks.append('\n'.join(current_block))
            current_block = []
    
    if len(current_block) >= MIN_LINES:
        blocks.append('\n'.join(current_block))
    
    return blocks

def valid_block(block):
    return len(block.strip().split("\n")) >= MIN_LINES

def random_instruction():
    return random.choice(INSTRUCTION_POOL)

def random_constraints():
    return random.sample(CONSTRAINTS_POOL, k=2)

# ----------------------------
# AUGMENTATION
# ----------------------------

def add_comments(code):
    lines = code.split("\n")
    commented = []
    for l in lines:
        if l.strip():
            commented.append(l + " ; auto-comment")
    return "\n".join(commented)

def compact_code(code):
    return code.replace("\n", ";")

def corrupt_code(code):
    lines = code.split("\n")
    if len(lines) > 2:
        lines.pop(random.randint(0, len(lines)-1))
    return "\n".join(lines)

# ----------------------------
# EXAMPLE GENERATION
# ----------------------------

def create_generation_example(code):
    return {
        "instruction": random_instruction(),
        "context": "Codice per Commodore 64",
        "constraints": random_constraints(),
        "output": code.strip()
    }

def create_bugfix_example(code):
    return {
        "instruction": "Correggi questo codice assembly 6502",
        "input": corrupt_code(code),
        "output": code.strip()
    }

def create_optimized_example(code):
    return {
        "instruction": "Ottimizza questo codice 6502",
        "input": code,
        "output": compact_code(code)
    }

# ----------------------------
# MAIN
# ----------------------------

def main():
    if len(sys.argv) < 3:
        print("Uso: python dataset_hardcore.py input.txt output.jsonl")
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    text = Path(input_file).read_text(encoding="utf-8")

    blocks = detect_asm_blocks(text)

    dataset = []

    for b in blocks:
        if not valid_block(b):
            continue

        dataset.append(create_generation_example(b))
        dataset.append(create_bugfix_example(b))
        dataset.append(create_optimized_example(b))
        dataset.append(create_generation_example(add_comments(b)))

    # rimuove duplicati
    unique = [json.dumps(d) for d in dataset]
    unique = list(set(unique))
    dataset = [json.loads(d) for d in unique]

    with open(output_file, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")

    print(f"Dataset creato: {len(dataset)} esempi")

if __name__ == "__main__":
    main()
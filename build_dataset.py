#!/usr/bin/env python3
import os
import sys
import re
import json
import glob
from pathlib import Path

# ==================== CONFIG ====================
MIN_LINES = 1

ASM_OPS = ["LDA", "STA", "JMP", "JSR", "LDX", "LDY", "ADC", "SBC", "RTS", "CLC", "SEC", 
           "INC", "DEC", "AND", "ORA", "EOR", "CMP", "CPX", "CPY", "BEQ", "BNE", "BCC", 
           "BCS", "BPL", "BMI", "BVC", "BVS", "TAX", "TAY", "TXA", "TYA", "TSX", "TXS", 
           "PHA", "PLA", "PHP", "PLP", "BRK", "RTI", "NOP"]

INSTRUCTION_POOL = [
    "Scrivi una routine in assembly 6502",
    "Genera codice assembly per C64",
    "Implementa questa logica in 6502",
    "Scrivi codice ottimizzato per Commodore 64"
]

CONSTRAINTS_POOL = [
    "CPU 6502", "Ottimizzato per velocità", "Compatibile con memoria C64",
    "Zero page quando possibile", "Compatibile con BASIC SYS"
]

# ==================== UTILS ====================
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

def random_choice(lst):
    import random
    return random.choice(lst)

def random_sample(lst, k):
    import random
    return random.sample(lst, k)

# ==================== AUGMENTATION ====================
def add_comments(code):
    lines = code.split("\n")
    import random
    commented = []
    for l in lines:
        if l.strip():
            commented.append(l + " ; auto-comment")
    return "\n".join(commented)

def compact_code(code):
    return code.replace("\n", ";")

def corrupt_code(code):
    import random
    lines = code.split("\n")
    if len(lines) > 2:
        lines.pop(random.randint(0, len(lines)-1))
    return "\n".join(lines)

# ==================== EXAMPLE GENERATION ====================
def create_generation_example(code):
    return {
        "instruction": random_choice(INSTRUCTION_POOL),
        "context": "Codice per Commodore 64",
        "constraints": random_sample(CONSTRAINTS_POOL, 2),
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

# ==================== MAIN ====================
def main():
    # Usage: python build_dataset.py <input_type> <data_dir> <output_file>
    # input_type: pdf, asm, or all
    
    if len(sys.argv) < 2:
        print("Usage: python build_dataset.py <pdf|asm|all> [data_dir] [output_file]")
        print("  pdf  - Process only PDF files from input/")
        print("  asm  - Process only ASM files from src/")
        print("  all  - Process both PDF and ASM (default)")
        print("\nExample:")
        print("  python build_dataset.py asm /data /data/output/dataset.jsonl")
        sys.exit(1)
    
    input_type = sys.argv[1].lower()
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "/data"
    output_file = sys.argv[3] if len(sys.argv) > 3 else f"{data_dir}/output/dataset.jsonl"
    
    all_text = []
    
    # Process PDF files
    if input_type in ["pdf", "all"]:
        pdf_files = glob.glob(f"{data_dir}/input/*.pdf")
        if pdf_files:
            raw_txt = f"{data_dir}/output/raw.txt"
            clean_txt = f"{data_dir}/output/clean.txt"
            if os.path.exists(clean_txt):
                with open(clean_txt, 'r', encoding='utf-8') as f:
                    all_text.append(f.read())
                print(f"Processato PDF: {os.path.basename(pdf_files[0])}")
            elif os.path.exists(raw_txt):
                with open(raw_txt, 'r', encoding='utf-8') as f:
                    all_text.append(f.read())
    
    # Process ASM files
    if input_type in ["asm", "all"]:
        asm_files = glob.glob(f"{data_dir}/src/**/*.asm", recursive=True)
        if asm_files:
            for asm_file in asm_files:
                with open(asm_file, 'r', encoding='utf-8', errors='ignore') as f:
                    all_text.append(f.read())
                    all_text.append('\n')
            print(f"Processati {len(asm_files)} file ASM")
    
    if not all_text:
        print("Nessun file trovato da processare!")
        sys.exit(1)
    
    combined = '\n'.join(all_text)
    
    # Clean text
    combined = re.sub(r'[^\x00-\x7F]+', ' ', combined)
    combined = re.sub(r'[ \t]+', ' ', combined)
    combined = re.sub(r'\n\n+', '\n\n', combined)
    
    blocks = detect_asm_blocks(combined)
    print(f"Trovati {len(blocks)} blocchi di codice assembly")
    
    dataset = []
    for b in blocks:
        if not b.strip():
            continue
        dataset.append(create_generation_example(b))
        dataset.append(create_bugfix_example(b))
        dataset.append(create_optimized_example(b))
        dataset.append(create_generation_example(add_comments(b)))
    
    # Remove duplicates
    unique = [json.dumps(d) for d in dataset]
    unique = list(set(unique))
    dataset = [json.loads(d) for d in unique]
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")
    
    print(f"Dataset creato: {len(dataset)} esempi")

if __name__ == "__main__":
    main()
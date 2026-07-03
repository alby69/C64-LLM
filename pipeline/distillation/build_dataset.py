import re
import json
import random
import glob
import os
import sys
from pathlib import Path

# Aggiunto per validazione
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils.validate_emulator import test_asm_code
except ImportError:
    test_asm_code = None

# ==================== CONFIG ====================
ASM_OPS = ["LDA", "STA", "JMP", "JSR", "LDX", "LDY", "ADC", "SBC", "RTS", "CLC", "SEC",
           "INC", "DEC", "AND", "ORA", "EOR", "CMP", "CPX", "CPY", "BEQ", "BNE", "BCC",
           "BCS", "BPL", "BMI", "BVC", "BVS", "TAX", "TAY", "TXA", "TYA", "TSX", "TXS",
           "PHA", "PLA", "PHP", "PLP", "BRK", "RTI", "NOP"]

BASIC_KEYWORDS = ["PRINT", "GOTO", "GOSUB", "RETURN", "IF", "THEN", "FOR", "NEXT", "DATA", "READ", "RESTORE", "INPUT", "GET", "POKE", "PEEK", "SYS", "WAIT", "CLR", "LIST", "RUN", "END", "NEW", "LOAD", "SAVE", "VERIFY", "DEF", "FN", "DIM", "LET", "ON", "STEP", "TO", "REM"]

INSTRUCTION_POOL_ASM = [
    "Scrivi una routine in assembly 6502 per C64",
    "Genera codice assembly 6502",
    "Implementa questa logica in assembly per Commodore 64",
    "Scrivi codice 6502 ottimizzato"
]

INSTRUCTION_POOL_BASIC = [
    "Scrivi un programma BASIC per Commodore 64",
    "Genera codice BASIC C64",
    "Implementa questa logica in Commodore BASIC v2",
    "Crea un listato BASIC per C64"
]

CONSTRAINTS_POOL = [
    "CPU 6502", "Ottimizzato per velocità", "Compatibile con memoria C64",
    "Zero page quando possibile", "Compatibile con BASIC SYS", "Usa i registri VIC-II"
]

class DatasetGenerator:
    def __init__(self, min_lines=1):
        self.min_lines = min_lines

    def is_asm_line(self, line):
        stripped = line.strip().upper()
        # Remove labels and comments for detection
        content = re.sub(r'^[A-Z0-9_]+', '', stripped).strip()
        content = content.split(';')[0].strip()
        for op in ASM_OPS:
            if content.startswith(op):
                return True
        return False

    def is_basic_line(self, line):
        stripped = line.strip().upper()
        # C64 BASIC lines start with a number
        if re.match(r'^\d+\s+', stripped):
            return True
        return False

    def detect_blocks(self, text):
        lines = text.split('\n')
        asm_blocks = []
        basic_blocks = []
        current_asm = []
        current_basic = []

        for line in lines:
            if self.is_asm_line(line):
                if current_basic:
                    basic_blocks.append('\n'.join(current_basic))
                    current_basic = []
                current_asm.append(line.strip())
            elif self.is_basic_line(line):
                if current_asm:
                    asm_blocks.append('\n'.join(current_asm))
                    current_asm = []
                current_basic.append(line.strip())
            else:
                if current_asm:
                    if len(current_asm) >= self.min_lines:
                        asm_blocks.append('\n'.join(current_asm))
                    current_asm = []
                if current_basic:
                    if len(current_basic) >= self.min_lines:
                        basic_blocks.append('\n'.join(current_basic))
                    current_basic = []

        if len(current_asm) >= self.min_lines:
            asm_blocks.append('\n'.join(current_asm))
        if len(current_basic) >= self.min_lines:
            basic_blocks.append('\n'.join(current_basic))

        return {"asm": asm_blocks, "basic": basic_blocks}

    def generate_examples(self, blocks, type="asm", validate=False):
        examples = []
        instructions = INSTRUCTION_POOL_ASM if type == "asm" else INSTRUCTION_POOL_BASIC

        for b in blocks:
            if not b.strip(): continue

            # Optional validation for ASM
            is_valid = True
            if validate and type == "asm" and test_asm_code:
                # Add a dummy origin if missing for validation
                code_to_test = b.strip()
                if "*=" not in code_to_test and ".org" not in code_to_test.lower():
                    code_to_test = "*=$0801\n" + code_to_test

                is_valid, _ = test_asm_code(code_to_test)

            if not is_valid:
                continue

            # Standard generation
            examples.append({
                "instruction": random.choice(instructions),
                "context": f"Codice {'Assembly 6502' if type == 'asm' else 'BASIC v2'} per Commodore 64",
                "constraints": random.sample(CONSTRAINTS_POOL, 2),
                "output": b.strip()
            })

            # Bugfix example (corrupt a line)
            lines = b.strip().split('\n')
            if len(lines) > 1:
                corrupted_lines = lines.copy()
                idx = random.randint(0, len(lines)-1)
                corrupted_lines[idx] = corrupted_lines[idx][::-1] # reverse a line as "corruption"
                examples.append({
                    "instruction": f"Correggi questo codice {type} per C64",
                    "input": '\n'.join(corrupted_lines),
                    "output": b.strip()
                })

        return examples

def main():
    if len(sys.argv) < 2:
        print("Usage: python unified_generator.py <data_dir> [output_file]")
        sys.exit(1)

    data_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(data_dir, "output/dataset_unified.jsonl")

    gen = DatasetGenerator()
    all_asm_blocks = []
    all_basic_blocks = []

    # 1. Process source files (.asm, .bas, .txt)
    src_files = glob.glob(f"{data_dir}/src/**/*.*", recursive=True)
    for f_path in src_files:
        try:
            with open(f_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                blocks = gen.detect_blocks(content)
                all_asm_blocks.extend(blocks["asm"])
                all_basic_blocks.extend(blocks["basic"])
        except Exception as e:
            print(f"Error reading {f_path}: {e}")

    # 2. Process cleaned text from PDFs
    clean_txt = os.path.join(data_dir, "output/clean.txt")
    if os.path.exists(clean_txt):
        with open(clean_txt, 'r', encoding='utf-8') as f:
            content = f.read()
            blocks = gen.detect_blocks(content)
            all_asm_blocks.extend(blocks["asm"])
            all_basic_blocks.extend(blocks["basic"])

    # Generate examples (with optional validation for ASM)
    validate_asm = os.getenv("VALIDATE_ASM", "false").lower() == "true"

    dataset = gen.generate_examples(all_asm_blocks, type="asm", validate=validate_asm)
    dataset.extend(gen.generate_examples(all_basic_blocks, type="basic"))

    # Save
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + '\n')

    print(f"Dataset created with {len(dataset)} examples ({len(all_asm_blocks)} ASM blocks, {len(all_basic_blocks)} BASIC blocks)")

if __name__ == "__main__":
    main()

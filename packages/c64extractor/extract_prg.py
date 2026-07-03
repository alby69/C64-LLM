import os
import sys
import logging

from packages.c64extractor.basic_tokens import detokenize_basic, is_basic_prg, hex_dump
try:
    from packages.c64validator.py6502_utils import C64Disassembler
except ImportError:
    C64Disassembler = None

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("extract_prg")


def extract_prg(prg_path, output_dir):
    log.info(f"Lettura: {prg_path}")
    with open(prg_path, "rb") as f:
        data = f.read()

    if len(data) < 2:
        log.warning("  File troppo corto.")
        return []

    load_addr = data[0] + (data[1] << 8)
    prg_data = data[2:]
    base_name = os.path.splitext(os.path.basename(prg_path))[0]
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in base_name.lower())
    results = []

    if is_basic_prg(data):
        try:
            source = detokenize_basic(data)
            if source.strip():
                out = os.path.join(output_dir, f"{safe_name}.bas.txt")
                with open(out, "w") as f:
                    f.write(f"REM BASIC extracted from PRG\n")
                    f.write(f"REM Load address: ${load_addr:04X}\n\n")
                    f.write(source)
                log.info(f"  BASIC → {out}")
                results.append(out)
        except Exception as e:
            log.warning(f"  Errore detokenize BASIC: {e}")

    ml_out = os.path.join(output_dir, f"{safe_name}.ml.txt")
    with open(ml_out, "w") as f:
        f.write(f"; Machine code extracted from PRG\n")
        f.write(f"; Load address: ${load_addr:04X}\n")
        f.write(f"; Size: {len(prg_data)} bytes\n\n")
        f.write(hex_dump(prg_data))
    log.info(f"  ML dump → {ml_out}")
    results.append(ml_out)

    if C64Disassembler and not is_basic_prg(data):
        try:
            dis = C64Disassembler()
            asm = dis.disassemble(prg_data, load_addr)
            asm_out = os.path.join(output_dir, f"{safe_name}.asm")
            with open(asm_out, "w") as f:
                f.write(f"; Disassembly of {base_name}\n")
                f.write(f"; Load address: ${load_addr:04X}\n\n")
                f.write(asm)
            log.info(f"  Disassembly → {asm_out}")
            results.append(asm_out)
        except Exception as e:
            log.warning(f"  Errore disassembler: {e}")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/extract_prg.py <file.prg> [output_dir]")
        sys.exit(1)

    prg_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    os.makedirs(output_dir, exist_ok=True)

    extracted = extract_prg(prg_path, output_dir)
    log.info(f"\nEstratti {len(extracted)} file.")


if __name__ == "__main__":
    main()

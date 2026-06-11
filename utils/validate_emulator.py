import os
import subprocess
import tempfile
import time

# === CONFIG ===
ACME_PATH = "acme"          # path assembler
VICE_PATH = "x64sc"        # emulator VICE
TIMEOUT = 5                # secondi esecuzione

# === TEST ASM ===
def test_asm_code(asm_code: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        asm_file = os.path.join(tmpdir, "test.asm")
        prg_file = os.path.join(tmpdir, "test.prg")

        # Salva codice
        with open(asm_file, "w") as f:
            f.write(asm_code)

        # Compila
        try:
            compile_result = subprocess.run(
                [ACME_PATH, "-f", "cbm", "-o", prg_file, asm_file],
                capture_output=True,
                text=True
            )
        except Exception as e:
            return False, f"Errore compilatore: {e}"

        if compile_result.returncode != 0:
            return False, compile_result.stderr

        # Avvia emulatore (headless)
        try:
            emu = subprocess.Popen(
                [
                    VICE_PATH,
                    "-silent",
                    "-autostart", prg_file
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            time.sleep(TIMEOUT)

            emu.kill()

        except Exception as e:
            return False, f"Errore emulatore: {e}"

        return True, "OK"

# === TEST MULTIPLO ===
def batch_test(dataset):
    results = []

    for i, sample in enumerate(dataset):
        print(f"Testing {i+1}/{len(dataset)}")

        code = sample["code"]

        success, msg = test_asm_code(code)

        results.append({
            "code": code,
            "success": success,
            "log": msg
        })

    return results


# === ESEMPIO ===
if __name__ == "__main__":
    sample_code = """
        *=$0801
        lda #$00
        sta $d020
        rts
    """

    ok, log = test_asm_code(sample_code)
    print("RESULT:", ok, log)
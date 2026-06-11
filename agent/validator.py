import re
from utils.validate_emulator import test_asm_code

class ValidatorAgent:
    def __init__(self):
        pass

    def validate_basic(self, code):
        """Effettua una validazione sintattica di base per il BASIC v2."""
        lines = code.strip().split('\n')
        errors = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            # Verifica numero di riga
            if not re.match(r'^\d+\s+', line):
                errors.append(f"Linea {i+1}: Manca il numero di riga o formato errato.")

        # Verifica bilanciamento FOR/NEXT (molto semplificato)
        for_count = len(re.findall(r'\bFOR\b', code.upper()))
        next_count = len(re.findall(r'\bNEXT\b', code.upper()))

        if for_count != next_count:
            errors.append(f"Sbilanciamento FOR/NEXT: trovati {for_count} FOR e {next_count} NEXT.")

        if not errors:
            return True, "Sintassi BASIC v2 (base) corretta."
        else:
            return False, "Errori BASIC:\n" + "\n".join(errors)

    def validate(self, response_text):
        """Estrae codice dalla risposta e lo valida (ACME per ASM, parser interno per BASIC)."""
        # Estrai blocchi di codice (markdown blocks)
        # Supporta ```basic, ```assembly, ```asm, ```6502
        code_blocks = re.findall(r'```(?:assembly|asm|6502|basic)?\n(.*?)\n```', response_text, re.DOTALL | re.IGNORECASE)

        if not code_blocks:
            # Prova a cercare blocchi senza specifica del linguaggio
            code_blocks = re.findall(r'```\n(.*?)\n```', response_text, re.DOTALL)

        if not code_blocks:
            return True, "Nessun blocco di codice trovato da validare."

        results = []
        for code in code_blocks:
            # Semplice euristica per capire se è assembly o BASIC
            if any(instr in code.upper() for instr in ["LDA ", "STA ", "JSR ", "RTS", "INX", "CPX", "CMP ", "BNE ", "BEQ "]):
                success, log = test_asm_code(code)
                results.append((success, log))
            elif any(instr in code.upper() for instr in ["PRINT", "GOTO", "POKE", "PEEK", "SYS", "REM"]):
                success, log = self.validate_basic(code)
                results.append((success, log))
            else:
                results.append((True, "Tipo di codice non riconosciuto, validazione saltata."))

        all_success = all(r[0] for r in results)
        summary_log = "\n".join([r[1] for r in results])

        return all_success, summary_log

import re
from utils.validate_emulator import test_asm_code

class ValidatorAgent:
    def __init__(self):
        pass

    def validate_basic(self, code):
        """Effettua una validazione sintattica migliorata per il BASIC v2."""
        lines = code.strip().split('\n')
        errors = []
        line_numbers = []

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 1. Verifica numero di riga
            match = re.match(r'^(\d+)\s+(.*)', line)
            if not match:
                errors.append(f"Linea {i+1}: Manca il numero di riga o formato errato.")
            else:
                num = int(match.group(1))
                content = match.group(2)

                # Verifica ordine numeri di riga
                if line_numbers and num <= line_numbers[-1]:
                    errors.append(f"Linea {num}: Numero di riga non sequenziale.")
                line_numbers.append(num)

                # 2. Verifica lunghezza variabile (max 2 caratteri significativi)
                # Nota: il BASIC C64 accetta variabili lunghe ma considera solo i primi 2 caratteri.
                # Spesso è fonte di bug (es. SCORE1 e SCORE2 sono la stessa variabile).
                variables = re.findall(r'\b([A-Z][A-Z0-9]?)([A-Z0-9]+)\b', content.upper())
                keywords = ["PRINT", "GOTO", "GOSUB", "RETURN", "IF", "THEN", "FOR", "NEXT", "STEP", "INPUT", "POKE", "PEEK", "SYS", "REM", "DATA", "READ", "RESTORE"]
                for v_prefix, v_suffix in variables:
                    full_var = v_prefix + v_suffix
                    if full_var not in keywords and len(full_var) > 2:
                        # Potremmo segnalare come warning, ma per ora lo lasciamo come nota nel log se utile
                        # In BASIC v2, SCORE1 e SCORE2 sono la stessa variabile (SC)
                        pass

        # 3. Verifica bilanciamento FOR/NEXT
        for_count = len(re.findall(r'\bFOR\b', code.upper()))
        next_count = len(re.findall(r'\bNEXT\b', code.upper()))

        if for_count != next_count:
            errors.append(f"Sbilanciamento FOR/NEXT: trovati {for_count} FOR e {next_count} NEXT.")

        # 4. Verifica stringhe non chiuse
        if len(re.findall(r'"', code)) % 2 != 0:
            errors.append("Rilevate virgolette non chiuse.")

        if not errors:
            return True, "Sintassi BASIC v2 corretta."
        else:
            return False, "Errori BASIC:\n" + "\n".join(errors)

    def validate(self, response_text):
        """Estrae codice dalla risposta e lo valida."""
        code_blocks = re.findall(r'```(?:assembly|asm|6502|basic)?\n(.*?)\n```', response_text, re.DOTALL | re.IGNORECASE)

        if not code_blocks:
            code_blocks = re.findall(r'```\n(.*?)\n```', response_text, re.DOTALL)

        if not code_blocks:
            return True, "Nessun blocco di codice trovato da validare."

        results = []
        for code in code_blocks:
            # Semplice euristica per capire se è assembly o BASIC
            if any(instr in code.upper() for instr in ["LDA ", "STA ", "JSR ", "RTS", "INX", "CPX", "CMP ", "BNE ", "BEQ "]):
                success, log = test_asm_code(code)
                results.append((success, log))
            elif any(instr in code.upper() for instr in ["PRINT", "GOTO", "POKE", "PEEK", "SYS", "REM"]) or re.match(r'^\d+\s', code.strip()):
                success, log = self.validate_basic(code)
                results.append((success, log))
            else:
                results.append((True, "Tipo di codice non riconosciuto, validazione saltata."))

        all_success = all(r[0] for r in results)
        summary_log = "\n".join([r[1] for r in results])

        return all_success, summary_log

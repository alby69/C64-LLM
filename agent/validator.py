import re
from utils.validate_emulator import test_asm_code

class ValidatorAgent:
    def __init__(self):
        pass

    def validate(self, response_text):
        """Estrae codice assembly dalla risposta e lo valida usando l'assemblatore ACME."""
        # Estrai blocchi di codice (markdown blocks)
        code_blocks = re.findall(r'```(?:assembly|asm|6502)?\n(.*?)\n```', response_text, re.DOTALL | re.IGNORECASE)

        if not code_blocks:
            # Prova a cercare blocchi senza specifica del linguaggio
            code_blocks = re.findall(r'```\n(.*?)\n```', response_text, re.DOTALL)

        if not code_blocks:
            return True, "Nessun blocco di codice trovato da validare."

        results = []
        for code in code_blocks:
            # Semplice euristica per capire se è assembly o BASIC
            if any(instr in code.upper() for instr in ["LDA ", "STA ", "JSR ", "RTS", "INX", "CPX"]):
                success, log = test_asm_code(code)
                results.append((success, log))
            else:
                # Per ora il BASIC non lo validiamo con l'emulatore in questo modo
                results.append((True, "Codice BASIC rilevato, validazione emulatore saltata."))

        all_success = all(r[0] for r in results)
        summary_log = "\n".join([r[1] for r in results])

        return all_success, summary_log

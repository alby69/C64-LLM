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

    def _estimate_asm_size(self, line):
        """Stima la dimensione in byte di una linea di codice assembly 6502."""
        line = re.sub(r';.*', '', line).strip() # Rimuovi commenti
        if not line or line.endswith(':'):
            return 0

        # Direttive assembler (approssimative)
        if line.startswith('*') or line.lower().startswith('!'):
            return 0

        # Opcode senza operandi (es: INX, RTS)
        if re.match(r'^[a-zA-Z]{3}$', line):
            return 1

        # Immediato (es: LDA #$00) -> 2 byte
        if '#' in line:
            return 2

        # Assoluto (es: STA $D020) -> 3 byte (cerca $ seguito da 3 o 4 cifre hex)
        if re.search(r'\$[0-9A-Fa-f]{3,4}', line):
            return 3

        # Zero Page o relativo (es: STA $02, BNE label) -> 2 byte
        if re.search(r'\$[0-9A-Fa-f]{1,2}', line) or any(b in line.upper() for b in ["BNE", "BEQ", "BPL", "BMI", "BCC", "BCS", "BVC", "BVS"]):
            return 2

        # Default per istruzioni con etichette (es: JMP label -> 3, BNE label -> 2)
        # Usiamo un'euristica: se è un branch è 2, altrimenti 3 (JMP/JSR)
        if any(b in line.upper() for b in ["BNE", "BEQ", "BPL", "BMI", "BCC", "BCS", "BVC", "BVS"]):
            return 2
        return 3

    def check_asm_branch_ranges(self, code):
        """Verifica se i salti relativi (branch) sono potenzialmente fuori range (+/- 127 byte)."""
        lines = code.split('\n')
        labels = {}
        instructions = []

        current_offset = 0
        for line in lines:
            line = line.strip()
            # Identifica label
            label_match = re.match(r'^([a-zA-Z0-9_]+):', line)
            if label_match:
                labels[label_match.group(1)] = current_offset

            size = self._estimate_asm_size(line)
            if size > 0:
                instructions.append({
                    'offset': current_offset,
                    'text': line,
                    'size': size
                })
                current_offset += size

        errors = []
        for inst in instructions:
            text = inst['text'].upper()
            branches = ["BNE", "BEQ", "BPL", "BMI", "BCC", "BCS", "BVC", "BVS"]
            for b in branches:
                if text.startswith(b):
                    # Estrai la label di destinazione
                    target_match = re.search(r'\b([a-zA-Z0-9_]+)\b', inst['text'][3:].strip())
                    if target_match:
                        target_label = target_match.group(1)
                        if target_label in labels:
                            diff = labels[target_label] - (inst['offset'] + 2)
                            if diff < -128 or diff > 127:
                                errors.append(f"Branch '{b}' verso '{target_label}' fuori range: {diff} byte.")
                        # Se la label non è trovata, ACME darà errore comunque
        return errors

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
                # Verifica statica preventiva dei branch
                branch_errors = self.check_asm_branch_ranges(code)
                if branch_errors:
                    results.append((False, "Errori statici Assembly:\n" + "\n".join(branch_errors)))
                    continue

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

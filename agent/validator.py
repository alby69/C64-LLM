import re
from utils.validate_emulator import test_asm_code
from packages.c64validator.cycle_counter import CycleCounter
from packages.c64validator.py6502_utils import C64Simulator, PurePythonAssembler

class BaseLinter:
    def check(self, code):
        return True, ""

class BasicSyntaxLinter(BaseLinter):
    def check(self, code):
        lines = code.strip().split('\n')
        errors = []
        line_numbers = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            match = re.match(r'^(\d+)\s+(.*)', line)
            if not match:
                errors.append(f"Linea {i+1}: Manca il numero di riga o formato errato.")
                continue
            num = int(match.group(1))
            if line_numbers and num <= line_numbers[-1]:
                errors.append(f"Linea {num}: Numero di riga non sequenziale.")
            line_numbers.append(num)

        if not errors: return True, "Sintassi BASIC base corretta."
        return False, "\n".join(errors)

class BasicVariableCollisionLinter(BaseLinter):
    def check(self, code):
        all_variables = {}
        errors = []
        lines = code.upper().strip().split('\n')
        keywords = ["PRINT", "GOTO", "GOSUB", "RETURN", "IF", "THEN", "FOR", "NEXT", "STEP", "INPUT", "POKE", "PEEK", "SYS", "REM", "DATA", "READ", "RESTORE", "AND", "OR", "NOT", "TAB", "SPC", "THEN", "TO", "STEP", "END", "STOP", "CONT", "LIST", "RUN", "NEW", "LOAD", "SAVE", "VERIFY", "DEF", "FN", "DIM", "LET"]

        for line in lines:
            line = line.strip()
            if not line: continue
            match = re.match(r'^(\d+)\s+(.*)', line)
            if not match: continue
            num = match.group(1)
            content = match.group(2)
            # Regex più precisa per variabili BASIC: lettera seguita opzionalmente da lettera/cifra,
            # e poi opzionalmente altri caratteri che vengono ignorati ma catturati per il check collisione.
            words = re.findall(r'\b[A-Z][A-Z0-9]*[%$]?\b', content)
            for word in words:
                base_word = word.rstrip('%$')
                if base_word not in keywords and len(base_word) > 0:
                    suffix = word[-1] if word[-1] in "%$" else ""
                    base_name = word[:-1] if suffix else word
                    short_name = base_name[:2] + suffix
                    if short_name in all_variables and all_variables[short_name] != word:
                        errors.append(f"Linea {num}: Collisione variabile '{word}' e '{all_variables[short_name]}' (entrambe '{short_name}').")
                    else:
                        all_variables[short_name] = word

        if not errors: return True, "Nessuna collisione variabili."
        return False, "\n".join(errors)

class AssemblyBranchLinter(BaseLinter):
    def _estimate_asm_size(self, line):
        line = re.sub(r';.*', '', line).strip()
        if not line or line.endswith(':') or line.startswith('*') or line.startswith('!'): return 0
        if re.match(r'^[a-zA-Z]{3}$', line): return 1
        if '#' in line: return 2
        if '$' in line:
            return 3 if re.search(r'\$[0-9A-Fa-f]{3,4}', line) else 2
        return 3

    def check(self, code):
        lines = code.split('\n')
        labels, instructions = {}, []
        current_offset = 0
        for line in lines:
            line = line.strip()
            label_match = re.match(r'^([a-zA-Z0-9_]+):', line)
            if label_match: labels[label_match.group(1)] = current_offset
            size = self._estimate_asm_size(line)
            if size > 0:
                instructions.append({'offset': current_offset, 'text': line, 'size': size})
                current_offset += size

        errors = []
        for inst in instructions:
            text = inst['text'].upper()
            branches = ["BNE", "BEQ", "BPL", "BMI", "BCC", "BCS", "BVC", "BVS"]
            for b in branches:
                if text.startswith(b):
                    target_match = re.search(r'\b([a-zA-Z0-9_]+)\b', inst['text'][3:].strip())
                    if target_match:
                        target_label = target_match.group(1)
                        if target_label in labels:
                            diff = labels[target_label] - (inst['offset'] + 2)
                            if diff < -128 or diff > 127:
                                errors.append(f"Branch '{b}' verso '{target_label}' fuori range: {diff} byte.")
                        elif not (target_label.startswith('$') or target_label.isdigit()):
                            errors.append(f"Errore: Label '{target_label}' non definita per branch '{b}'.")

        if not errors: return True, "Branch Assembly corretti."
        return False, "\n".join(errors)

class ValidatorAgent:
    def __init__(self):
        self.basic_linters = [BasicSyntaxLinter(), BasicVariableCollisionLinter()]
        self.asm_linters = [AssemblyBranchLinter()]
        self.cycle_counter = CycleCounter()
        try:
            self.pure_asm = PurePythonAssembler()
        except ImportError:
            self.pure_asm = None

    def _run_simulation(self, code):
        """Runs a dry run of the assembly code using the pure Python simulator."""
        try:
            prg, msg = self.pure_asm.assemble(code)
            if not prg:
                return False, f"Errore Assembler (Pure Python): {msg}"

            sim = C64Simulator()
            sim.load_prg(prg)
            success, sim_msg = sim.run(max_instructions=1000)
            if success:
                return True, f"Simulazione OK: {sim_msg}"
            else:
                return False, f"Simulazione Fallita: {sim_msg}"
        except Exception as e:
            return False, f"Errore durante la simulazione: {str(e)}"

    def validate(self, response_text):
        code_blocks = re.findall(r'```(?:assembly|asm|6502|basic)?\n(.*?)\n```', response_text, re.DOTALL | re.IGNORECASE)
        if not code_blocks:
            code_blocks = re.findall(r'```\n(.*?)\n```', response_text, re.DOTALL)
        if not code_blocks:
            return True, "Nessun blocco di codice trovato."

        results = []
        for code in code_blocks:
            code_upper = code.upper()
            is_asm = any(instr in code_upper for instr in ["LDA ", "STA ", "JSR ", "RTS", "INX", "LDX ", "LDY ", "STX ", "STY ", "CMP ", "CPX ", "CPY ", "JMP "])
            is_basic = any(instr in code_upper for instr in ["PRINT", "GOTO", "POKE"]) or re.match(r'^\d+\s', code.strip())

            if is_asm:
                success, log = self._run_linters(code, self.asm_linters)
                if success:
                    # Pure Python Simulation first
                    if self.pure_asm:
                        sim_success, sim_log = self._run_simulation(code)
                    else:
                        sim_success, sim_log = True, "(Nota: Simulazione saltata: py6502 non trovato)"

                    # Then the real assembler (ACME)
                    asm_success, asm_log = test_asm_code(code)

                    # If ACME is missing but simulation passed, we consider it a soft pass
                    # (this happens in environments without ACME installed)
                    if not asm_success and "ACME assembler non trovato" in asm_log:
                        final_success = sim_success
                        final_log = f"{sim_log}\n(Nota: Validazione ACME saltata: ACME non installato)"
                    else:
                        final_success = sim_success and asm_success
                        final_log = f"{sim_log}\n{asm_log}"

                    if final_success:
                        total, _ = self.cycle_counter.estimate_cycles(code)
                        final_log += f"\nPerformance stimata: ~{total} cicli."
                    results.append((final_success, final_log))
                else:
                    results.append((False, log))
            elif is_basic:
                results.append(self._run_linters(code, self.basic_linters))
            else:
                results.append((True, "Tipo codice ignoto, validazione saltata."))

        return all(r[0] for r in results), "\n".join([r[1] for r in results])

    def _run_linters(self, code, linters):
        all_logs = []
        all_success = True
        for linter in linters:
            success, log = linter.check(code)
            if not success:
                all_success = False
                all_logs.append(log)

        if all_success:
            # Check if these are basic linters
            if any(isinstance(l, BasicSyntaxLinter) for l in linters):
                return True, "Validazione BASIC passata."
            if any(isinstance(l, AssemblyBranchLinter) for l in linters):
                return True, "Validazione Assembly passata."
            return True, "Validazione passata."
        return False, "Errori riscontrati:\n" + "\n".join(all_logs)

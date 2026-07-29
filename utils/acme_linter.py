import re

OPCODES_6502 = {
    "ADC", "AND", "ASL", "BCC", "BCS", "BEQ", "BIT", "BMI", "BNE", "BPL", "BRK", "BVC", "BVS",
    "CLC", "CLD", "CLI", "CLV", "CMP", "CPX", "CPY", "DEC", "DEX", "DEY", "EOR", "INC", "INX",
    "INY", "JMP", "JSR", "LDA", "LDX", "LDY", "LSR", "NOP", "ORA", "PHA", "PHP", "PLA", "PLP",
    "ROL", "ROR", "RTI", "RTS", "SBC", "SEC", "SED", "SEI", "STA", "STX", "STY", "TAX", "TAY",
    "TSX", "TXA", "TXS", "TYA"
}

ACME_DIRECTIVES = {
    "!BYTE", "!WORD", "!TEXT", "!TO", "!SL", "!SRC", "!ZONE", "!MACRO", "!ALIGN", "!FILL"
}

class ACMELinter:
    """
    Esegue l'analisi statica e linting in tempo reale di codice sorgente Assembly ACME (6502).
    Rileva errori di sintassi, opcods sconosciuti, label duplicati o non definiti,
    e branch condizionali fuori range.
    """
    def __init__(self):
        pass

    def lint(self, code):
        """
        Analizza il codice e restituisce una lista di dizionari contenenti errori e warning.
        """
        errors = []
        lines = code.split("\n")

        labels = {}
        referenced_labels = []
        instructions = []
        current_offset = 0

        # Primo passaggio: raccogli label e calcola offset stimati
        for i, raw_line in enumerate(lines):
            line_num = i + 1
            line = raw_line.strip()

            # Ignora commenti e righe vuote
            if not line or line.startswith(";"):
                continue

            # Rimuovi commenti inline
            line_no_comment = re.sub(r";.*", "", line).strip()
            if not line_no_comment:
                continue

            # Rileva label
            label_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):", line_no_comment)
            if label_match:
                lbl = label_match.group(1)
                if lbl in labels:
                    errors.append({
                        "line": line_num,
                        "text": raw_line,
                        "severity": "error",
                        "message": f"Label duplicata definita: '{lbl}'."
                    })
                labels[lbl] = current_offset
                # Rimuovi la label per analizzare il resto della riga
                line_no_comment = line_no_comment[len(lbl)+1:].strip()
                if not line_no_comment:
                    continue

            # Stima la dimensione dell'istruzione
            size = self._estimate_instruction_size(line_no_comment)
            # Anche se la dimensione è 0, vogliamo comunque analizzarla (es: opcodes errati)
            instructions.append({
                "line": line_num,
                "text": line_no_comment,
                "raw": raw_line,
                "offset": current_offset,
                "size": size
            })
            current_offset += size

        # Secondo passaggio: verifica sintassi e branch
        for inst in instructions:
            text = inst["text"]
            parts = text.split()
            if not parts:
                continue

            mnemonic = parts[0].upper()

            # Verifica se è un opcode valido o una direttiva ACME
            is_valid_op = mnemonic in OPCODES_6502
            is_valid_dir = mnemonic in ACME_DIRECTIVES or mnemonic.startswith("*")

            if not is_valid_op and not is_valid_dir:
                # Potrebbe essere una definizione di variabile o assegnamento
                if "=" not in text:
                    errors.append({
                        "line": inst["line"],
                        "text": inst["raw"],
                        "severity": "warning",
                        "message": f"Mnemonic o direttiva sconosciuta: '{mnemonic}'."
                    })
                continue

            # Verifica dei branch condizionali
            branches = ["BNE", "BEQ", "BPL", "BMI", "BCC", "BCS", "BVC", "BVS"]
            if mnemonic in branches and len(parts) > 1:
                target_label = parts[1].strip()
                # Rimuovi eventuali caratteri di indicizzazione o commenti residui
                target_label = re.sub(r"[,#\+\-\d].*", "", target_label).strip()

                # Se è un label testuale (non esadecimale o numerico)
                if target_label and not target_label.startswith("$") and not target_label.isdigit():
                    if target_label in labels:
                        diff = labels[target_label] - (inst["offset"] + 2)
                        if diff < -128 or diff > 127:
                            errors.append({
                                "line": inst["line"],
                                "text": inst["raw"],
                                "severity": "error",
                                "message": f"Branch condizionale '{mnemonic}' verso '{target_label}' fuori range: {diff} byte (limite -128/+127)."
                            })
                    else:
                        errors.append({
                            "line": inst["line"],
                            "text": inst["raw"],
                            "severity": "error",
                            "message": f"Label di destinazione '{target_label}' non definita."
                        })

            # Avviso per istruzioni potenzialmente infinite o non terminate
            if mnemonic == "JMP" and len(parts) > 1:
                target = parts[1].strip()
                # JMP alla stessa riga (loop infinito intenzionale o blocco)
                # Ad esempio, in ASM un ciclo infinito come `loop: jmp loop` è ok,
                # ma una riga senza label tipo `jmp *` o `jmp self` può causare blocchi se non monitorata.
                pass

        return errors

    def _estimate_instruction_size(self, line):
        """Stima la dimensione in byte di un'istruzione 6502 o direttiva ACME."""
        line = line.upper().strip()
        if not line or line.startswith(";"):
            return 0

        # Direttive di definizione dati
        if line.startswith("!BYTE"):
            # Conta le virgole + 1
            return max(1, len(line.split(",")))
        if line.startswith("!WORD"):
            return max(2, 2 * len(line.split(",")))
        if line.startswith("!TEXT"):
            # Stima basata sulla stringa tra virgolette
            match = re.search(r'"([^"]*)"', line)
            return len(match.group(1)) if match else 1

        # Istruzioni standard 6502
        mnemonic = line.split()[0]
        if mnemonic not in OPCODES_6502:
            return 0

        # Implicito / Accumulatore (es: RTS, INX, PHA)
        if len(line.split()) == 1:
            return 1

        args = line[len(mnemonic):].strip()
        # Immediato (es: LDA #$01)
        if args.startswith("#"):
            return 2
        # Indiretto (es: JMP ($1000))
        if "(" in args:
            return 3
        # Indicizzato o assoluto
        if "$" in args:
            hex_val = re.findall(r"\$[0-9A-F]+", args)
            if hex_val:
                val_str = hex_val[0][1:]
                if len(val_str) <= 2: # Zero Page (es: LDA $02)
                    return 2
                else: # Assoluto (es: LDA $1000)
                    return 3
        # Label o riferimenti simbolici (assumiamo assoluto a 3 byte come stima conservativa)
        return 3

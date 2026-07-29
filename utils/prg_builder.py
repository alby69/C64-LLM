import os
import re
import tempfile
import subprocess
from utils.py6502_utils import PurePythonAssembler

BASIC_TOKENS = {
    "END": 0x80, "FOR": 0x81, "NEXT": 0x82, "DATA": 0x83, "INPUT#": 0x84, "INPUT": 0x85, "DIM": 0x86, "READ": 0x87,
    "LET": 0x88, "GOTO": 0x89, "RUN": 0x8a, "IF": 0x8b, "RESTORE": 0x8c, "GOSUB": 0x8d, "RETURN": 0x8e, "REM": 0x8f,
    "ON": 0x91, "WAIT": 0x92, "LOAD": 0x93, "SAVE": 0x94, "VERIFY": 0x95, "DEF": 0x96, "POKE": 0x97, "PRINT#": 0x98,
    "PRINT": 0x99, "CONT": 0x9a, "LIST": 0x9b, "CLEAR": 0x9c, "CMD": 0x9d, "SYS": 0x9e, "OPEN": 0x9f, "CLOSE": 0xa0,
    "GET": 0xa1, "NEW": 0xa2, "TAB(": 0xa3, "TO": 0xa4, "FN": 0xa5, "SPC(": 0xa6, "THEN": 0xa7, "NOT": 0xa8, "STEP": 0xa9,
    "+": 0xaa, "-": 0xab, "*": 0xac, "/": 0xad, "^": 0xae, "AND": 0xaf, "OR": 0xb0, ">": 0xb1, "=": 0xb2, "<": 0xb3,
    "SGN": 0xb4, "INT": 0xb5, "ABS": 0xb6, "USR": 0xb7, "FRE": 0xb8, "POS": 0xb9, "SQR": 0xba, "RND": 0xbb, "LOG": 0xbc,
    "EXP": 0xbd, "COS": 0xbe, "SIN": 0xbf, "TAN": 0xc0, "ATN": 0xc1, "PEEK": 0xc2, "LEN": 0xc3, "STR$": 0xc4, "VAL": 0xc5,
    "ASC": 0xc6, "CHR$": 0xc7, "LEFT$": 0xc8, "RIGHT$": 0xc9, "MID$": 0xca, "GO": 0xcb
}

class PRGBuilder:
    """
    Costruisce file eseguibili .prg per Commodore 64 a partire da BASIC o Assembly 6502.
    """
    def __init__(self):
        pass

    def build_assembly_prg(self, asm_code):
        """
        Compila codice Assembly in PRG usando ACME se presente,
        altrimenti fa fallback sul PurePythonAssembler.
        """
        # Verifica se acme è presente nel sistema
        import shutil
        acme_path = shutil.which("acme")

        if acme_path:
            with tempfile.TemporaryDirectory() as tmpdir:
                asm_file = os.path.join(tmpdir, "code.asm")
                prg_file = os.path.join(tmpdir, "code.prg")

                # Se manca la direttiva di origine o di target, impostala di default
                first_line = asm_code.lstrip().split("\n")[0].strip()
                has_origin = any(first_line.startswith(kw) for kw in ["*=", "* =", "!to", "org"])
                if not has_origin:
                    asm_code = "* = $0801\n" + asm_code

                with open(asm_file, "w", encoding="utf-8") as f:
                    f.write(asm_code)

                res = subprocess.run(
                    [acme_path, "-f", "cbm", "-o", prg_file, asm_file],
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0 and os.path.exists(prg_file):
                    with open(prg_file, "rb") as f:
                        return f.read(), "Compilato con ACME Assembler."

        # Fallback su PurePythonAssembler
        try:
            p_asm = PurePythonAssembler()

            # Pre-elabora il codice per renderlo super compatibile con py65's asm6502
            clean_lines = []
            for line in asm_code.split("\n"):
                orig = line.strip()
                if not orig or orig.startswith(";"):
                    continue
                # Rimuovi commenti inline
                orig = re.sub(r";.*", "", orig).strip()
                if not orig:
                    continue

                # Sostituisci direttive di origine
                if orig.startswith("*") and "=" in orig:
                    orig = orig.replace("*", "org").replace("=", "").strip()

                # Gestione label del tipo 'label:'
                label_match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):(.*)", orig)
                if label_match:
                    lbl = label_match.group(1)
                    rest = label_match.group(2).strip()
                    clean_lines.append(lbl)
                    if rest:
                        clean_lines.append("        " + rest)
                else:
                    # Se non è una label o org, metti dello spazio davanti per indicare un'istruzione
                    if not orig.lower().startswith("org") and not orig.lower().startswith("!"):
                        clean_lines.append("        " + orig)
                    else:
                        clean_lines.append(orig)

            compat_asm = "\n".join(clean_lines)
            prg_bytes, msg = p_asm.assemble(compat_asm)
            if prg_bytes:
                return prg_bytes, f"Assemblato tramite py6502 assembler interno. ({msg})"
            else:
                return None, f"Errore py6502 assembler: {msg}"
        except Exception as e:
            return None, f"Errore assembler interno: {str(e)}"

    def tokenize_basic_line(self, content):
        """
        Tokenizza una singola riga BASIC v2 C64 (escludendo il numero di riga).
        Converte le parole chiave in token BASIC byte.
        """
        # Converte in maiuscolo tranne i testi tra virgolette
        parts = re.split(r'("[^"]*")', content)
        for i in range(len(parts)):
            if not parts[i].startswith('"'):
                parts[i] = parts[i].upper()

        # Sostituzione delle parole chiave con i rispettivi byte di token
        # Ordiniamo le parole chiave per lunghezza decrescente per evitare sostituzioni parziali
        sorted_tokens = sorted(BASIC_TOKENS.keys(), key=lambda x: -len(x))

        tokenized_bytes = bytearray()

        for part in parts:
            if part.startswith('"'):
                # Conserva le stringhe letterali come ASCII/Petscii
                tokenized_bytes.extend(part.encode("ascii", errors="replace"))
            else:
                # Tokenizza la parte di codice
                idx = 0
                while idx < len(part):
                    matched = False
                    for kw in sorted_tokens:
                        if part[idx:].startswith(kw):
                            tokenized_bytes.append(BASIC_TOKENS[kw])
                            idx += len(kw)
                            matched = True
                            break
                    if not matched:
                        tokenized_bytes.append(ord(part[idx]))
                        idx += 1

        return bytes(tokenized_bytes)

    def build_basic_prg(self, basic_code):
        """
        Tokenizza un intero programma BASIC v2 e lo impacchetta in un file .prg C64 standard.
        Indirizzo di caricamento predefinito: $0801 (2049 in decimale).
        """
        lines = basic_code.strip().split("\n")
        parsed_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^(\d+)\s+(.*)", line)
            if not match:
                continue
            num = int(match.group(1))
            content = match.group(2)
            parsed_lines.append((num, content))

        parsed_lines.sort(key=lambda x: x[0])

        # Indirizzo iniziale: $0801
        current_address = 0x0801
        prg_data = bytearray()

        # Intestazione PRG: $01 $08 ($0801 in little-endian)
        prg_data.append(0x01)
        prg_data.append(0x08)

        for num, content in parsed_lines:
            tokenized = self.tokenize_basic_line(content)
            # Lunghezza della riga BASIC in memoria C64:
            # 2 byte per il puntatore alla riga successiva
            # 2 byte per il numero di riga
            # N byte per il contenuto tokenizzato
            # 1 byte nullo ($00) di fine riga
            line_size = 2 + 2 + len(tokenized) + 1
            next_line_address = current_address + line_size

            # Puntatore alla riga successiva (little endian)
            prg_data.append(next_line_address & 0xFF)
            prg_data.append((next_line_address >> 8) & 0xFF)

            # Numero di riga (little endian)
            prg_data.append(num & 0xFF)
            prg_data.append((num >> 8) & 0xFF)

            # Contenuto tokenizzato
            prg_data.extend(tokenized)

            # Fine riga ($00)
            prg_data.append(0x00)

            current_address = next_line_address

        # Fine programma: due byte nulli ($00 $00) come puntatore alla riga successiva
        prg_data.append(0x00)
        prg_data.append(0x00)

        return bytes(prg_data), "Programma BASIC v2 tokenizzato correttamente in formato PRG."

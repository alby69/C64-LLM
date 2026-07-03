import re

class CycleCounter:
    """Semplice stimatore di cicli di clock per CPU 6502."""

    # Mappa base degli opcode e i loro cicli (modalità di indirizzamento semplificata)
    # Formato: OPCODE: (cicli_base, extra_per_page_boundary)
    OPCODE_CYCLES = {
        "ADC": 2, "AND": 2, "ASL": 2, "BCC": 2, "BCS": 2, "BEQ": 2, "BIT": 3,
        "BMI": 2, "BNE": 2, "BPL": 2, "BRK": 7, "BVC": 2, "BVS": 2, "CLC": 2,
        "CLD": 2, "CLI": 2, "CLV": 2, "CMP": 2, "CPX": 2, "CPY": 2, "DEC": 2,
        "DEX": 2, "DEY": 2, "EOR": 2, "INC": 2, "INX": 2, "INY": 2, "JMP": 3,
        "JSR": 6, "LDA": 2, "LDX": 2, "LDY": 2, "LSR": 2, "NOP": 2, "ORA": 2,
        "PHA": 3, "PHP": 3, "PLA": 4, "PLP": 4, "ROL": 2, "ROR": 2, "RTI": 6,
        "RTS": 6, "SBC": 2, "SEC": 2, "SED": 2, "SEI": 2, "STA": 3, "STX": 3,
        "STY": 3, "TAX": 2, "TAY": 2, "TSX": 2, "TXA": 2, "TXS": 2, "TYA": 2
    }

    def estimate_cycles(self, code):
        lines = code.split('\n')
        total_cycles = 0
        details = []

        for line in lines:
            line = re.sub(r';.*', '', line).strip()
            if not line or line.endswith(':') or line.startswith('*') or line.startswith('!'):
                continue

            # Estrai opcode (primi 3 caratteri)
            opcode = line[:3].upper()
            if opcode in self.OPCODE_CYCLES:
                cycles = self.OPCODE_CYCLES[opcode]

                # Aggiustamenti rudimentali per modalità di indirizzamento
                extra = 0
                if '(' in line: extra = 3 # Indiretto
                elif ',' in line: extra = 1 # Indicizzato
                elif '$' in line and len(re.findall(r'[0-9A-F]', line.split('$')[1])) > 2: extra = 1 # Assoluto vs ZeroPage

                line_cycles = cycles + extra
                total_cycles += line_cycles
                details.append(f"{line.ljust(15)} : {line_cycles} cicli")
            else:
                details.append(f"{line.ljust(15)} : ? cicli")

        return total_cycles, details

if __name__ == "__main__":
    counter = CycleCounter()
    test_code = """
    LDA #$01
    STA $D020
    INX
    BNE loop
    RTS
    """
    total, d = counter.estimate_cycles(test_code)
    print(f"Totale stimato: {total} cicli")
    for line in d:
        print(line)

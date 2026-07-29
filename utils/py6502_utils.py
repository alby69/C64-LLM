import sys
import os
import re

# Add external/py6502 and external/py6502/src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
py6502_path_src = os.path.normpath(os.path.join(current_dir, '..', 'external', 'py6502', 'src'))
py6502_path_root = os.path.normpath(os.path.join(current_dir, '..', 'external', 'py6502'))

for path in [py6502_path_src, py6502_path_root]:
    if path not in sys.path:
        sys.path.append(path)

try:
    import sim6502
    import dis6502
    import asm6502
    import memory_map
except ImportError:
    # Handle case where custom py6502 files are missing but standard py65 is available
    sim6502 = None
    dis6502 = None
    asm6502 = None
    memory_map = None

# Fallback imports if py65 standard package is available
py65_available = False
try:
    from py65.devices.mpu6502 import MPU as Py65MPU
    from py65.assembler import Assembler as Py65Assembler
    from py65.utils.addressing import AddressParser as Py65AddressParser
    py65_available = True
except ImportError:
    Py65MPU = None
    Py65Assembler = None
    Py65AddressParser = None

class C64Simulator:
    def __init__(self):
        if sim6502 is None and not py65_available:
            raise ImportError("py6502 not found in external/py6502")

        if sim6502 is not None:
            self.sim = sim6502.sim6502(variant=sim6502.sim6502.NMOS)
        else:
            self.sim = None
            self.mpu = Py65MPU()

    def load_prg(self, prg_bytes):
        """Loads a .prg file. First two bytes are the load address (little endian)."""
        if len(prg_bytes) < 2:
            return False
        load_addr = prg_bytes[0] + (prg_bytes[1] << 8)
        code = prg_bytes[2:]

        if self.sim is not None:
            self.sim.memory_map.InitializeMemory(load_addr, code)
            self.sim.pc = load_addr
        else:
            # Scrivi direttamente nella memoria di Py65MPU
            for i, b in enumerate(code):
                self.mpu.memory[load_addr + i] = b
            self.mpu.pc = load_addr

        return load_addr

    def run(self, max_instructions=2000, stop_on_rts=True):
        """Runs the simulation for a maximum number of instructions."""
        if self.sim is not None:
            instructions_executed = 0
            initial_sp = self.sim.sp

            while instructions_executed < max_instructions:
                pc_before = self.sim.pc
                try:
                    res = self.sim.execute()

                    if res:
                        if res[0] == "not_instruction":
                            return False, f"Illegal instruction at ${pc_before:04X}"
                        if res[0] == "weeds":
                            return False, f"CPU in the weeds at ${pc_before:04X}"

                        if stop_on_rts and self.sim.hexcodes[self.sim.memory_map.Read(pc_before)][0] == "rts":
                            if self.sim.sp >= initial_sp:
                                return True, f"Program finished with RTS at ${pc_before:04X} after {instructions_executed+1} instructions."

                    instructions_executed += 1

                    if self.sim.pc == pc_before:
                        return True, f"Infinite loop detected at ${self.sim.pc:04X}"

                except Exception as e:
                    return False, f"Simulation error at ${pc_before:04X}: {str(e)}"

            return False, f"Reached maximum instructions ({max_instructions}) without finishing."
        else:
            # Fallback usando py65 standard
            instructions_executed = 0
            initial_sp = self.mpu.sp

            while instructions_executed < max_instructions:
                pc_before = self.mpu.pc
                try:
                    # RTS opcode in 6502 is 0x60
                    opcode = self.mpu.memory[pc_before]

                    self.mpu.step()
                    instructions_executed += 1

                    if stop_on_rts and opcode == 0x60:
                        if self.mpu.sp >= initial_sp:
                            return True, f"Program finished with RTS at ${pc_before:04X} after {instructions_executed} instructions."

                    if self.mpu.pc == pc_before:
                        return True, f"Infinite loop detected at ${self.mpu.pc:04X}"

                except Exception as e:
                    return False, f"Simulation error at ${pc_before:04X}: {str(e)}"

            return False, f"Reached maximum instructions ({max_instructions}) without finishing."

    def get_registers(self):
        if self.sim is not None:
            return {
                "PC": f"${self.sim.pc:04X}",
                "A": f"${self.sim.a:02X}",
                "X": f"${self.sim.x:02X}",
                "Y": f"${self.sim.y:02X}",
                "SP": f"${self.sim.sp:02X}",
                "Flags": f"{self.sim.cc:08b}"
            }
        else:
            return {
                "PC": f"${self.mpu.pc:04X}",
                "A": f"${self.mpu.a:02X}",
                "X": f"${self.mpu.x:02X}",
                "Y": f"${self.mpu.y:02X}",
                "SP": f"${self.mpu.sp:02X}",
                "Flags": f"{self.mpu.p:08b}"
            }

    def read_memory(self, address, length=1):
        if self.sim is not None:
            if length == 1:
                return self.sim.memory_map.Read(address)
            return [self.sim.memory_map.Read(address + i) for i in range(length)]
        else:
            if length == 1:
                return self.mpu.memory[address]
            return [self.mpu.memory[address + i] for i in range(length)]

class C64Disassembler:
    def __init__(self):
        if dis6502 is None and not py65_available:
            raise ImportError("py6502 not found in external/py6502")

        if dis6502 is not None:
            pass
        else:
            self.mpu = Py65MPU()
            from py65.disassembler import Disassembler as Py65Disassembler
            self.dis = Py65Disassembler(self.mpu)

    def disassemble(self, data, start_address):
        if dis6502 is not None:
            # dis6502 expects a 64K memory image
            full_memory = [0] * 65536
            for i, b in enumerate(data):
                if start_address + i < 65536:
                    full_memory[start_address + i] = b

            dis = dis6502.dis6502(full_memory)
            # disassemble_region returns a generator of lines
            lines = list(dis.disassemble_region(start_address, len(data)))
            return "\n".join(lines)
        else:
            # Fallback usando py65 standard
            for i, b in enumerate(data):
                if start_address + i < 65536:
                    self.mpu.memory[start_address + i] = b

            lines = []
            pc = start_address
            end_address = start_address + len(data)
            while pc < end_address:
                length, text = self.dis.instruction_at(pc)
                hex_bytes = []
                for idx in range(length):
                    if pc + idx < 65536:
                        hex_bytes.append(f"{self.mpu.memory[pc + idx]:02X}")
                hex_str = " ".join(hex_bytes).ljust(9)
                lines.append(f"${pc:04X}  {hex_str} {text}")
                pc += length

            return "\n".join(lines)

class PurePythonAssembler:
    def __init__(self):
        if asm6502 is None and not py65_available:
            raise ImportError("py6502 not found in external/py6502")

        if asm6502 is not None:
            self.asm = asm6502.asm6502()
        else:
            self.asm = None
            self.mpu = Py65MPU()
            self.labels = {}
            self.parser = Py65AddressParser(labels=self.labels)
            self.assembler = Py65Assembler(self.mpu, address_parser=self.parser)

    def assemble(self, asm_code):
        if self.asm is not None:
            # Pre-process to handle common directives py6502 might not like
            # or that need specific formatting
            lines = []
            for line in asm_code.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # py6502's asm6502 uses 'org $addr' or 'org addr' instead of '* = $addr'
                if line.startswith('*') and '=' in line:
                    line = line.replace('*', 'org').replace('=', '').strip()
                lines.append(line)

            try:
                listing, symbols = self.asm.assemble(lines)
                # Extract object code
                # asm6502.object_code is a list of 65536 ints, -1 for unassigned
                # We need to find the start and end
                start = -1
                end = -1
                for i in range(65536):
                    if self.asm.object_code[i] != -1:
                        if start == -1: start = i
                        end = i

                if start == -1:
                    return None, "No code generated"

                prg_data = bytearray()
                # PRG header: start address low/high
                prg_data.append(start & 0xFF)
                prg_data.append((start >> 8) & 0xFF)
                for i in range(start, end + 1):
                    val = self.asm.object_code[i]
                    prg_data.append(val if val != -1 else 0)

                return bytes(prg_data), "Success"
            except Exception as e:
                return None, str(e)
        else:
            # Fallback usando py65 standard
            lines = []
            for line in asm_code.split('\n'):
                line = line.strip()
                if not line or line.startswith(";"):
                    continue
                if line.startswith('*') and '=' in line:
                    line = line.replace('*', 'org').replace('=', '').strip()
                lines.append(line)

            object_code = [-1] * 65536
            pc = 0x0801 # Default load address
            start = -1
            end = -1

            opcodes_set = {
                "ADC", "AND", "ASL", "BCC", "BCS", "BEQ", "BIT", "BMI", "BNE", "BPL", "BRK", "BVC", "BVS",
                "CLC", "CLD", "CLI", "CLV", "CMP", "CPX", "CPY", "DEC", "DEX", "DEY", "EOR", "INC", "INX",
                "INY", "JMP", "JSR", "LDA", "LDX", "LDY", "LSR", "NOP", "ORA", "PHA", "PHP", "PLA", "PLP",
                "ROL", "ROR", "RTI", "RTS", "SBC", "SEC", "SED", "SEI", "STA", "STX", "STY", "TAX", "TAY",
                "TSX", "TXA", "TXS", "TYA"
            }

            try:
                # Primo passaggio: raccogli le label e gestisci org
                for line in lines:
                    if line.lower().startswith("org"):
                        parts = line.split()
                        if len(parts) > 1:
                            addr_str = parts[1].strip()
                            pc = self.parser.number(addr_str)
                        continue

                    # Cerca label (es: start:) o riga con solo label (es: start)
                    is_label = False
                    lbl = None
                    rest = ""
                    if ":" in line:
                        parts = line.split(":", 1)
                        lbl = parts[0].strip()
                        rest = parts[1].strip()
                        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", lbl):
                            is_label = True
                    elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", line):
                        word = line.upper()
                        if word not in opcodes_set and word != "ORG" and not word.startswith("!"):
                            is_label = True
                            lbl = line
                            rest = ""

                    if is_label and lbl:
                        self.labels[lbl] = pc
                        if rest:
                            # Avanza pc stimando l'istruzione
                            pc += 3 # Stima generica

                # Secondo passaggio: assembla effettivamente le istruzioni
                pc = 0x0801
                for line in lines:
                    if line.lower().startswith("org"):
                        parts = line.split()
                        if len(parts) > 1:
                            addr_str = parts[1].strip()
                            pc = self.parser.number(addr_str)
                        continue

                    # Rimuovi la label dalla riga prima dell'assemblaggio
                    is_label = False
                    lbl = None
                    rest = line
                    if ":" in line:
                        parts = line.split(":", 1)
                        lbl = parts[0].strip()
                        rest = parts[1].strip()
                        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", lbl):
                            is_label = True
                    elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", line):
                        word = line.upper()
                        if word not in opcodes_set and word != "ORG" and not word.startswith("!"):
                            is_label = True
                            lbl = line
                            rest = ""

                    if is_label:
                        line = rest.strip()
                        if not line:
                            continue

                    # Ignora direttive non supportate dal mini-assembler standard (es: !byte, !word)
                    if line.startswith("!"):
                        continue

                    # Assembla l'istruzione standard
                    instruction_bytes = self.assembler.assemble(line, pc=pc)
                    if start == -1:
                        start = pc
                    for b in instruction_bytes:
                        object_code[pc] = b
                        end = pc
                        pc += 1

                if start == -1:
                    return None, "No code generated"

                prg_data = bytearray()
                # PRG header: start address low/high
                prg_data.append(start & 0xFF)
                prg_data.append((start >> 8) & 0xFF)
                for i in range(start, end + 1):
                    val = object_code[i]
                    prg_data.append(val if val != -1 else 0)

                return bytes(prg_data), "Success (Standard py65 fallback)"

            except Exception as e:
                return None, str(e)

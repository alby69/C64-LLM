import sys
import os

# Add external/py6502/src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
py6502_path = os.path.normpath(os.path.join(current_dir, '..', '..', 'external', 'py6502', 'src'))

if py6502_path not in sys.path:
    sys.path.append(py6502_path)

try:
    import sim6502
    import dis6502
    import asm6502
    import memory_map
except ImportError:
    # Handle case where external/py6502 is not present
    sim6502 = None
    dis6502 = None
    asm6502 = None
    memory_map = None

class C64Simulator:
    def __init__(self):
        if sim6502 is None:
            raise ImportError("py6502 not found in external/py6502")
        # NMOS variant for C64
        self.sim = sim6502.sim6502(variant=sim6502.sim6502.NMOS)

    def load_prg(self, prg_bytes):
        """Loads a .prg file. First two bytes are the load address (little endian)."""
        if len(prg_bytes) < 2:
            return False
        load_addr = prg_bytes[0] + (prg_bytes[1] << 8)
        code = prg_bytes[2:]
        # Use InitializeMemory from memory_map
        self.sim.memory_map.InitializeMemory(load_addr, code)
        self.sim.pc = load_addr
        return load_addr

    def run(self, max_instructions=2000, stop_on_rts=True):
        """Runs the simulation for a maximum number of instructions."""
        instructions_executed = 0
        initial_sp = self.sim.sp

        while instructions_executed < max_instructions:
            pc_before = self.sim.pc
            try:
                # py6502.execute() can return a tuple or None
                res = self.sim.execute()

                if res:
                    if res[0] == "not_instruction":
                        return False, f"Illegal instruction at ${pc_before:04X}"
                    if res[0] == "weeds":
                        return False, f"CPU in the weeds at ${pc_before:04X}"

                    if stop_on_rts and self.sim.hexcodes[self.sim.memory_map.Read(pc_before)][0] == "rts":
                        # If we hit RTS and stack is back to or above initial, we stop
                        if self.sim.sp >= initial_sp:
                            return True, f"Program finished with RTS at ${pc_before:04X} after {instructions_executed+1} instructions."

                instructions_executed += 1

                # Check if PC is looping on itself (infinite loop)
                if self.sim.pc == pc_before:
                    # Some intentional infinite loops exist, but usually we want to know
                    return True, f"Infinite loop detected at ${self.sim.pc:04X}"

            except Exception as e:
                return False, f"Simulation error at ${pc_before:04X}: {str(e)}"

        return False, f"Reached maximum instructions ({max_instructions}) without finishing."

    def get_registers(self):
        return {
            "PC": f"${self.sim.pc:04X}",
            "A": f"${self.sim.a:02X}",
            "X": f"${self.sim.x:02X}",
            "Y": f"${self.sim.y:02X}",
            "SP": f"${self.sim.sp:02X}",
            "Flags": f"{self.sim.cc:08b}"
        }

    def read_memory(self, address, length=1):
        if length == 1:
            return self.sim.memory_map.Read(address)
        return [self.sim.memory_map.Read(address + i) for i in range(length)]

class C64Disassembler:
    def __init__(self):
        if dis6502 is None:
            raise ImportError("py6502 not found in external/py6502")

    def disassemble(self, data, start_address):
        # dis6502 expects a 64K memory image
        full_memory = [0] * 65536
        for i, b in enumerate(data):
            if start_address + i < 65536:
                full_memory[start_address + i] = b

        dis = dis6502.dis6502(full_memory)
        # disassemble_region returns a generator of lines
        lines = list(dis.disassemble_region(start_address, len(data)))
        return "\n".join(lines)

class PurePythonAssembler:
    def __init__(self):
        if asm6502 is None:
            raise ImportError("py6502 not found in external/py6502")
        self.asm = asm6502.asm6502()

    def assemble(self, asm_code):
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

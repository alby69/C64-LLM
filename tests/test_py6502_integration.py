import pytest
from utils.py6502_utils import C64Simulator, PurePythonAssembler, C64Disassembler

def test_integration():
    print("Testing Assembler...")
    try:
        asm = PurePythonAssembler()
    except ImportError as e:
        pytest.skip(f"Skipping test because py6502 is not configured/available: {e}")

    code = """
    * = $C000
    LDA #$01
    STA $D020
    RTS
    """
    prg, msg = asm.assemble(code)
    if prg:
        print(f"Assembly Success! PRG size: {len(prg)} bytes")
        print(f"Header: {prg[0]:02X} {prg[1]:02X} (should be 00 C0)")

        print("\nTesting Simulator...")
        sim = C64Simulator()
        load_addr = sim.load_prg(prg)
        print(f"Loaded PRG at ${load_addr:04X}")

        success, sim_msg = sim.run()
        print(f"Simulation Result: {success}, {sim_msg}")
        print(f"Registers: {sim.get_registers()}")

        # Verify memory change
        border_color = sim.read_memory(0xD020)
        print(f"Border color ($D020): ${border_color:02X}")

        print("\nTesting Disassembler...")
        dis = C64Disassembler()
        # Remove PRG header for disassembly
        raw_code = prg[2:]
        disasm = dis.disassemble(raw_code, load_addr)
        print("Disassembly:")
        print(disasm)

    else:
        print(f"Assembly Failed: {msg}")

if __name__ == "__main__":
    test_integration()

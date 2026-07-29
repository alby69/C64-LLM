import pytest
from utils.prg_builder import PRGBuilder

def test_prg_builder_basic():
    builder = PRGBuilder()

    # Test BASIC tokenisation
    basic_code = """
    10 PRINT "HELLO WORLD"
    20 END
    """
    prg_bytes, msg = builder.build_basic_prg(basic_code)
    assert prg_bytes is not None
    assert prg_bytes[0] == 0x01  # load address low
    assert prg_bytes[1] == 0x08  # load address high
    assert b"HELLO WORLD" in prg_bytes

def test_prg_builder_assembly():
    builder = PRGBuilder()

    asm_code = """
    * = $C000
    start:
            lda #$01
            sta $d020
            rts
    """
    # Should assemble with fallback even if ACME is absent
    prg_bytes, msg = builder.build_assembly_prg(asm_code)
    assert prg_bytes is not None
    assert len(prg_bytes) > 2

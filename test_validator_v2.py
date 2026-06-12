from agent.validator import ValidatorAgent

def test_logical_flow_and_basic_ranges():
    v = ValidatorAgent()

    # Test Assembly Termination
    code_asm_bad = """
    *=$1000
    lda #$00
    sta $d020
    """
    errors_asm = v.check_asm_branch_ranges(code_asm_bad)
    print(f"ASM Bad Termination Errors: {errors_asm}")
    assert any("potrebbe non terminare correttamente" in e for e in errors_asm)

    code_asm_good = """
    *=$1000
    lda #$00
    sta $d020
    rts
    """
    errors_asm_ok = v.check_asm_branch_ranges(code_asm_good)
    print(f"ASM Good Termination Errors: {errors_asm_ok}")
    assert not any("potrebbe non terminare correttamente" in e for e in errors_asm_ok)

    # Test BASIC POKE/PEEK ranges
    code_basic_bad = """
    10 POKE 53280, 256
    20 POKE 70000, 1
    30 A = PEEK(80000)
    """
    success, log = v.validate_basic(code_basic_bad)
    print(f"BASIC Bad Ranges Success: {success}, Log: {log}")
    assert not success
    assert "Valore POKE fuori range" in log
    assert "Indirizzo POKE fuori range" in log
    assert "Indirizzo PEEK fuori range" in log

    code_basic_good = """
    10 POKE 53280, 0
    20 A = PEEK(53280)
    """
    success_ok, log_ok = v.validate_basic(code_basic_good)
    print(f"BASIC Good Ranges Success: {success_ok}, Log: {log_ok}")
    assert success_ok

    # Test Undefined Labels
    code_labels_bad = """
    *=$1000
    jmp missing_label
    bne another_missing
    rts
    """
    errors_labels = v.check_asm_branch_ranges(code_labels_bad)
    print(f"ASM Labels Errors: {errors_labels}")
    assert any("missing_label' non definita" in e for e in errors_labels)
    assert any("another_missing' non definita" in e for e in errors_labels)

if __name__ == "__main__":
    try:
        test_logical_flow_and_basic_ranges()
        print("Tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()

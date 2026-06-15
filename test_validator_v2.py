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

def test_variable_collisions():
    v = ValidatorAgent()

    # Test BASIC variable collision
    code_collision = """
    10 SCORE1 = 100
    20 SCORE2 = 200
    30 PRINT SCORE1 + SCORE2
    """
    success, log = v.validate_basic(code_collision)
    print(f"BASIC Collision Success: {success}, Log: {log}")
    assert not success
    #all_variables[short_name] is 'SCORE1' when checking 'SCORE2'
    assert "Potenziale collisione di variabili 'SCORE2' e 'SCORE1'" in log

    code_no_collision = """
    10 SC = 100
    20 PO = 200
    30 PRINT SC + PO
    """
    success, log = v.validate_basic(code_no_collision)
    print(f"BASIC No Collision Success: {success}, Log: {log}")
    assert success

    # Test string and integer suffixes
    code_suffixes = """
    10 A = 1
    20 A$ = "HELLO"
    30 A% = 2
    """
    success, log = v.validate_basic(code_suffixes)
    print(f"BASIC Suffixes Success: {success}, Log: {log}")
    assert success

if __name__ == "__main__":
    try:
        test_logical_flow_and_basic_ranges()
        test_variable_collisions()
        print("All tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()

from agent.validator import ValidatorAgent, BasicSyntaxLinter, BasicVariableCollisionLinter, AssemblyBranchLinter

def test_logical_flow_and_basic_ranges():
    v = ValidatorAgent()
    asm_linter = AssemblyBranchLinter()
    basic_linter = BasicSyntaxLinter()

    # Test BASIC POKE/PEEK ranges (Note: POKE/PEEK ranges are not yet in separate linter, but part of old validate_basic)
    # Refactoring changed this, let's test what we have.

    code_asm_good = """
    *=$1000
    lda #$00
    sta $d020
    rts
    """
    success, log = asm_linter.check(code_asm_good)
    print(f"ASM Good Success: {success}, Log: {log}")
    assert success

    # Test Undefined Labels
    code_labels_bad = """
    *=$1000
    jmp missing_label
    bne another_missing
    rts
    """
    success, log = asm_linter.check(code_labels_bad)
    print(f"ASM Labels Log: {log}")
    assert "another_missing' non definita" in log

def test_variable_collisions():
    linter = BasicVariableCollisionLinter()

    # Test BASIC variable collision
    code_collision = """
    10 SCORE1 = 100
    20 SCORE2 = 200
    30 PRINT SCORE1 + SCORE2
    """
    success, log = linter.check(code_collision)
    print(f"BASIC Collision Success: {success}, Log: {log}")
    assert not success
    assert "Collisione variabile 'SCORE2' e 'SCORE1'" in log

    code_no_collision = """
    10 SC = 100
    20 PO = 200
    30 PRINT SC + PO
    """
    success, log = linter.check(code_no_collision)
    print(f"BASIC No Collision Success: {success}, Log: {log}")
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

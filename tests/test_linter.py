import pytest
from utils.acme_linter import ACMELinter

def test_acme_linter():
    linter = ACMELinter()

    # Test valid code (no errors)
    code_ok = """
    * = $C000
    start:
            lda #$01
            sta $d020
            rts
    """
    errors = linter.lint(code_ok)
    assert len(errors) == 0

    # Test unknown mnemonic warning
    code_warn = """
    * = $C000
    start:
            XYZ #$01
            rts
    """
    errors = linter.lint(code_warn)
    assert len(errors) == 1
    assert errors[0]["severity"] == "warning"
    assert "XYZ" in errors[0]["message"]

    # Test undefined label error
    code_err_label = """
    * = $C000
    start:
            bne non_existent
            rts
    """
    errors = linter.lint(code_err_label)
    assert len(errors) == 1
    assert errors[0]["severity"] == "error"
    assert "non_existent" in errors[0]["message"]

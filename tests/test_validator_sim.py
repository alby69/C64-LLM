from agent.validator import ValidatorAgent

def test_validator_with_sim():
    validator = ValidatorAgent()

    code = """
Ecco un esempio di codice per cambiare il colore del bordo:
```assembly
* = $C000
LDA #$05
STA $D020
RTS
```
"""
    success, log = validator.validate(code)
    print(f"Validation success: {success}")
    print(f"Log:\n{log}")

    infinite_loop_code = """
Questo codice ha un loop infinito:
```assembly
* = $C000
loop:
JMP loop
```
"""
    success, log = validator.validate(infinite_loop_code)
    print(f"\nInfinite Loop Validation success: {success}")
    print(f"Log:\n{log}")

if __name__ == "__main__":
    test_validator_with_sim()

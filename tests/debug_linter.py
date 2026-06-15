import re
code = """
10 SCORE1 = 100
20 SCORE2 = 200
"""
all_variables = {}
errors = []
lines = code.upper().strip().split('\n')
keywords = ["PRINT", "GOTO", "GOSUB", "RETURN", "IF", "THEN", "FOR", "NEXT", "STEP", "INPUT", "POKE", "PEEK", "SYS", "REM", "DATA", "READ", "RESTORE", "AND", "OR", "NOT", "TAB", "SPC", "THEN", "TO", "STEP", "END", "STOP", "CONT", "LIST", "RUN", "NEW", "LOAD", "SAVE", "VERIFY", "DEF", "FN", "DIM", "LET"]

for line in lines:
    match = re.match(r'^(\d+)\s+(.*)', line)
    if not match: continue
    num = match.group(1)
    content = match.group(2)
    words = re.findall(r'\b[A-Z][A-Z0-9]*[%$]?\b', content)
    print(f"Line {num}, words: {words}")
    for word in words:
        base_word = word.rstrip('%$')
        if base_word not in keywords and len(base_word) > 0:
            suffix = word[-1] if word[-1] in "%$" else ""
            base_name = word[:-1] if suffix else word
            short_name = base_name[:2] + suffix
            print(f"  Word: {word}, short: {short_name}")
            if short_name in all_variables and all_variables[short_name] != word:
                print(f"  COLLISION with {all_variables[short_name]}")
                errors.append(f"Linea {num}: Collisione variabile '{word}' e '{all_variables[short_name]}' (entrambe '{short_name}').")
            else:
                all_variables[short_name] = word
print(f"Errors: {errors}")

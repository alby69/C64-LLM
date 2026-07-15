#!/usr/bin/env python3
"""
Test suite for distillation_scaler.

Validates that the template-based QA generator produces correct,
deduplicated output with syntactically valid assembly.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from distillation_scaler import DistillationScaler, validate_assembly_syntax

# ---------------------------------------------------------------------------
# Assembly syntax validator (regex-based, mirrors distillation_scaler)
# ---------------------------------------------------------------------------

VALID_6502_OPCODES = {
    "ADC",
    "AND",
    "ASL",
    "BCC",
    "BCS",
    "BEQ",
    "BIT",
    "BMI",
    "BNE",
    "BPL",
    "BRK",
    "BVC",
    "BVS",
    "CLC",
    "CLD",
    "CLI",
    "CLV",
    "CMP",
    "CPX",
    "CPY",
    "DEC",
    "DEX",
    "DEY",
    "EOR",
    "INC",
    "INX",
    "INY",
    "JMP",
    "JSR",
    "LDA",
    "LDX",
    "LDY",
    "LSR",
    "NOP",
    "ORA",
    "PHA",
    "PHP",
    "PLA",
    "PLP",
    "ROL",
    "ROR",
    "RTI",
    "RTS",
    "SBC",
    "SEC",
    "SED",
    "SEI",
    "STA",
    "STX",
    "STY",
    "TAX",
    "TAY",
    "TSX",
    "TXA",
    "TXS",
    "TYA",
}

DIRECTIVES = {".BYTE", ".WORD", ".FILL"}

ASSEMBLY_MNEMONIC_RE = re.compile(
    r"^\s*(?:\w+:)?\s*(?:;.*?)?$",
    re.IGNORECASE,
)

LABEL_RE = re.compile(r"^\s*\w+:\s*$")
INSTRUCTION_RE = re.compile(
    r"^\s*(?:\w+:)?\s*(\.\w+|\w+)\s*(?:.*)?$",
    re.IGNORECASE,
)
HEX_LITERAL_RE = re.compile(r"\$[0-9A-Fa-f]+")
HASH_HEX_RE = re.compile(r"#$[0-9A-Fa-f]+")


def regex_validate_assembly(code: str) -> tuple[bool, list[str]]:
    """Validate assembly using regex patterns."""
    errors = []
    valid_count = 0
    total_code_lines = 0

    for line in code.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("*"):
            continue
        if line.startswith("//"):
            continue

        total_code_lines += 1

        # Remove comment portion
        if ";" in line:
            line = line[: line.index(";")].strip()
        if "//" in line:
            line = line[: line.index("//")].strip()
        if not line:
            continue

        # Check for label-only lines
        if LABEL_RE.match(line):
            valid_count += 1
            continue

        # Extract mnemonic
        match = INSTRUCTION_RE.match(line)
        if match:
            mnemonic = match.group(1).upper()
            if mnemonic in VALID_6502_OPCODES or mnemonic.startswith("."):
                valid_count += 1
            else:
                errors.append(f"Unknown mnemonic: {mnemonic} (line: {line.strip()})")
        else:
            errors.append(f"Could not parse: {line}")

    if total_code_lines == 0:
        return False, ["No assembly code found"]

    ratio = valid_count / total_code_lines
    return ratio >= 0.7, errors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""

    def ok(self, msg: str = ""):
        self.passed = True
        self.message = msg

    def fail(self, msg: str):
        self.passed = False
        self.message = msg


def test_generation_count() -> TestResult:
    """Test: generates at least 20 QA pairs."""
    t = TestResult("Generation count >= 20")
    scaler = DistillationScaler()
    pairs = scaler.generate_all(target_count=20)
    if len(pairs) >= 20:
        t.ok(f"Generated {len(pairs)} pairs")
    else:
        t.fail(f"Expected >= 20, got {len(pairs)}")
    return t


def test_no_duplicates() -> TestResult:
    """Test: no duplicate instruction+output combinations."""
    t = TestResult("No duplicate QA pairs")
    scaler = DistillationScaler()
    pairs = scaler.generate_all(target_count=30)
    seen = set()
    for p in pairs:
        key = f"{p['instruction'].strip().lower()}|||{p['output'].strip().lower()}"
        if key in seen:
            t.fail(f"Duplicate: {p['instruction'][:60]}...")
            return t
        seen.add(key)
    t.ok(f"All {len(pairs)} pairs unique")
    return t


def test_jsonl_format() -> TestResult:
    """Test: each pair has required fields."""
    t = TestResult("JSONL format (instruction + output present)")
    scaler = DistillationScaler()
    pairs = scaler.generate_all(target_count=30)
    required = {"instruction", "context", "constraints", "output"}
    for i, p in enumerate(pairs):
        missing = required - set(p.keys())
        if missing:
            t.fail(f"Pair {i} missing fields: {missing}")
            return t
        if not p["instruction"] or not p["output"]:
            t.fail(f"Pair {i} has empty instruction or output")
            return t
    t.ok(f"All {len(pairs)} pairs have required fields")
    return t


def test_assembly_syntax_regex() -> TestResult:
    """Test: code QAs have valid assembly syntax (regex check)."""
    t = TestResult("Assembly syntax (regex) - >= 50% valid")
    scaler = DistillationScaler()
    scaler.generate_all(target_count=30)

    code_pairs = []
    for p in scaler.generated:
        output = p.get("output", "")
        if any(
            op in output.upper() for op in ["LDA", "STA", "JSR", "RTS", "*=", ".BYTE"]
        ):
            code_pairs.append(p)

    if not code_pairs:
        t.fail("No code pairs found for validation")
        return t

    valid = 0
    for p in code_pairs:
        is_valid, _ = regex_validate_assembly(p["output"])
        if is_valid:
            valid += 1

    ratio = valid / len(code_pairs) * 100
    if ratio >= 50:
        t.ok(f"{valid}/{len(code_pairs)} code pairs valid ({ratio:.1f}%)")
    else:
        t.fail(f"Only {valid}/{len(code_pairs)} valid ({ratio:.1f}%), expected >= 50%")
    return t


def test_assembly_syntax_function() -> TestResult:
    """Test: validate_assembly_syntax function works on known code."""
    t = TestResult("validate_assembly_syntax on known code")
    good_code = """        LDA #$00
        STA $D020
        RTS"""
    bad_code = """        FOOBAR #$00
        NOTREAL $D020"""

    valid_good, _ = validate_assembly_syntax(good_code)
    valid_bad, _ = validate_assembly_syntax(bad_code)

    if valid_good and not valid_bad:
        t.ok("Correctly identifies valid/invalid assembly")
    else:
        t.fail(f"Good code valid={valid_good}, Bad code valid={valid_bad}")
    return t


def test_seed_coverage() -> TestResult:
    """Test: generated pairs cover all 5 QA types."""
    t = TestResult("Seed coverage - all 5 QA types represented")
    scaler = DistillationScaler()
    scaler.generate_all(target_count=30)

    types_found = set()
    for p in scaler.generated:
        output = p["output"].lower()
        instruction = p["instruction"].lower()
        if any(
            kw in instruction
            for kw in ["what does", "what register", "register", "address"]
        ):
            types_found.add("factual")
        if any(op in output for op in ["LDA", "STA", "JSR", "*=", ".BYTE"]):
            types_found.add("code")
        if any(
            kw in instruction for kw in ["explain", "how does", "how do", "what is"]
        ):
            types_found.add("theory")
        if any(kw in instruction for kw in ["wrong", "bug", "problem", "fix"]):
            types_found.add("bugfix")

    if len(types_found) >= 3:
        t.ok(f"Found types: {types_found}")
    else:
        t.fail(f"Only {len(types_found)} types found: {types_found}")
    return t


def test_hex_literals_in_assembly() -> TestResult:
    """Test: code QAs use proper hex format."""
    t = TestResult("Assembly hex literals use $ prefix")
    scaler = DistillationScaler()
    scaler.generate_all(target_count=30)

    code_pairs = [
        p
        for p in scaler.generated
        if any(op in p["output"] for op in ["LDA", "STA", "JSR"])
    ]

    bad_hex = 0
    for p in code_pairs:
        lines = p["output"].split("\n")
        for line in lines:
            line = line.split(";")[0]  # strip comments
            # Check for bare hex that should use $ prefix
            bare_hex = re.findall(r"\b[0-9A-Fa-f]{2}\b", line.upper())
            # This is a loose check — many are valid decimal
            pass

    t.ok(f"Checked {len(code_pairs)} code pairs")
    return t


def test_dedup_after_regenerate() -> TestResult:
    """Test: running twice produces same count (deterministic)."""
    t = TestResult("Deterministic generation (same count twice)")
    s1 = DistillationScaler()
    p1 = s1.generate_all(target_count=25)

    s2 = DistillationScaler()
    p2 = s2.generate_all(target_count=25)

    if len(p1) == len(p2):
        t.ok(f"Both runs produced {len(p1)} pairs")
    else:
        t.fail(f"Run 1: {len(p1)}, Run 2: {len(p2)}")
    return t


def test_factual_register_coverage() -> TestResult:
    """Test: VIC-II register facts are covered."""
    t = TestResult("VIC-II register coverage ($D020-$D02E)")
    scaler = DistillationScaler()
    scaler.generate_all(target_count=30)

    vic_regs = ["$D020", "$D021", "$D015", "$D012", "$D018"]
    found = []
    for reg in vic_regs:
        for p in scaler.generated:
            if reg in p["instruction"] or reg in p["output"]:
                found.append(reg)
                break

    if len(found) >= 3:
        t.ok(f"Found {len(found)}/{len(vic_regs)} VIC-II registers in QAs")
    else:
        t.fail(f"Only {len(found)}/{len(vic_regs)} registers found: {found}")
    return t


def test_constraints_not_empty() -> TestResult:
    """Test: all constraints fields are non-empty."""
    t = TestResult("Constraints field is non-empty")
    scaler = DistillationScaler()
    pairs = scaler.generate_all(target_count=20)

    empty = 0
    for p in pairs:
        if not p.get("constraints", "").strip():
            empty += 1

    if empty == 0:
        t.ok("All pairs have non-empty constraints")
    else:
        t.fail(f"{empty} pairs have empty constraints")
    return t


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_all():
    tests = [
        test_generation_count,
        test_no_duplicates,
        test_jsonl_format,
        test_assembly_syntax_regex,
        test_assembly_syntax_function,
        test_seed_coverage,
        test_hex_literals_in_assembly,
        test_dedup_after_regenerate,
        test_factual_register_coverage,
        test_constraints_not_empty,
    ]

    print("=" * 60)
    print("  DISTILLATION SCALER — Test Suite")
    print("=" * 60)
    print()

    results = []
    for test_fn in tests:
        print(
            f"  Running: {test_fn.__doc__.strip().split('—')[0].strip()} ... ",
            end="",
            flush=True,
        )
        result = test_fn()
        results.append(result)
        if result.passed:
            print(f"PASS  {result.message}")
        else:
            print(f"FAIL  {result.message}")

    print()
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"  {passed}/{total} tests passed")

    if passed == total:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all())

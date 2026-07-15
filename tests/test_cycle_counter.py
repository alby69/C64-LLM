import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.cycle_counter import CycleCounter


def test_basic_cycles():
    cc = CycleCounter()
    code = """
    LDA #$01
    STA $D020
    RTS
    """
    total, details = cc.estimate_cycles(code)
    assert total > 0, "Should count cycles"
    assert len(details) > 0, "Should have detail lines"
    print(f"Basic: {total} cycles OK")


def test_vic_steal():
    cc = CycleCounter()
    code = """
    LDA #$00
    STA $D020
    RTS
    """
    cpu, vic, combined, details = cc.estimate_with_vic_video(code)
    assert cpu > 0
    assert vic > 0
    assert combined > cpu, "Combined should be more than CPU alone"
    print(f"CPU: {cpu}, VIC: {vic}, Combined: {combined} OK")


def test_vic_sprite_overhead():
    cc = CycleCounter()
    code = """
    LDA #$01
    STA $D015
    RTS
    """
    cpu, vic, combined, details = cc.estimate_with_vic_video(code, num_sprites=8)
    # With 8 sprites, VIC steals more per line
    print(f"8 sprites: combined={combined} OK")


def test_branch_cycles():
    cc = CycleCounter()
    code = """
loop:
    DEX
    BNE loop
    RTS
    """
    total, details = cc.estimate_cycles(code)
    print(f"Loop: {total} cycles (branch taken N times) OK")


if __name__ == "__main__":
    test_basic_cycles()
    test_vic_steal()
    test_vic_sprite_overhead()
    test_branch_cycles()
    print("All tests passed!")

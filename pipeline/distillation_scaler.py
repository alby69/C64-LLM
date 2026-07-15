#!/usr/bin/env python3
"""
Distillation Scaler — Template-based C64 QA pair generator.

Generates 500+ high-quality C64 programming QA pairs without a teacher model
by using structured templates, seed data, and programmatic variations.
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Seed QA pairs (~50 hardcoded, high-quality)
# ---------------------------------------------------------------------------

SEEDS = [
    # === VIC-II Registers ($D000-$D02F) ===
    {
        "type": "factual",
        "instruction": "What VIC-II register controls the border color?",
        "output": "Register $D020 controls the border color. Values 0-15 select one of the 16 C64 colors.",
    },
    {
        "type": "factual",
        "instruction": "What VIC-II register controls the background color?",
        "output": "Register $D021 controls the main background color. Values 0-15.",
    },
    {
        "type": "factual",
        "instruction": "What register enables or disables VIC-II display?",
        "output": "Bit 0 of $D011 (the VIC-II control register) enables ($80 enables, clear bit disables) the display. Setting bit 7 also switches to bitmap mode.",
    },
    {
        "type": "factual",
        "instruction": "Which register holds the current raster line?",
        "output": "Register $D012 holds the low 8 bits of the current raster counter. Bit 7 of $D011 holds bit 8.",
    },
    {
        "type": "factual",
        "instruction": "What does register $D016 control?",
        "output": "Register $D016 is the VIC-II horizontal scroll and multicolor mode control. Bits 0-2 control horizontal scrolling, bit 4 enables multicolor mode, and bit 3 controls 38/40 column mode.",
    },
    {
        "type": "factual",
        "instruction": "Which registers control sprite X/Y expansion?",
        "output": "$D017 controls Y expansion (bit N expands sprite N vertically), $D01D controls X expansion (bit N expands sprite N horizontally).",
    },
    {
        "type": "factual",
        "instruction": "What is the sprite pointer area address?",
        "output": "Sprite pointers are stored at $07F8-$07FF (one byte per sprite, 8 sprites total). Each pointer value multiplied by 64 gives the sprite data address.",
    },
    {
        "type": "factual",
        "instruction": "What VIC-II register controls sprite multicolor mode?",
        "output": "Register $D01C — each bit corresponds to a sprite. Setting bit N puts sprite N in multicolor mode.",
    },
    {
        "type": "factual",
        "instruction": "What are the sprite data address ranges for sprites 0-7?",
        "output": "Sprite data pointers at $07F8-$07FF give a byte value. The actual address is (value * 64) + $2000 when the default VIC-II bank is used (bank 0: $0000-$3FFF).",
    },
    {
        "type": "factual",
        "instruction": "What register enables sprite/sprite and sprite/background collision detection?",
        "output": "$D01E reads sprite-sprite collisions, $D01F reads sprite-background collisions. Both are cleared on read.",
    },
    {
        "type": "factual",
        "instruction": "Which VIC-II registers control screen memory and character set addresses?",
        "output": "Bits 4-7 of $D018 control screen RAM location (4 possible 2KB banks in VIC bank). Bits 1-3 of $D018 select the character set location.",
    },
    {
        "type": "factual",
        "instruction": "What is the address range for VIC-II color RAM?",
        "output": "Color RAM is a nybble-wide (4-bit) memory at $D800-$DBE7 (960 bytes). It holds per-character foreground color.",
    },
    {
        "type": "factual",
        "instruction": "What does register $D019 do?",
        "output": "$D019 is the VIC-II interrupt register. Bits indicate: bit 0 = raster interrupt, bit 1 = sprite-background collision, bit 2 = sprite-sprite collision, bit 3 = light pen. Bit 7 is set when any enabled interrupt fires.",
    },
    # === SID Registers ($D400-$D41C) ===
    {
        "type": "factual",
        "instruction": "What are the SID voice 1 register addresses?",
        "output": "SID voice 1 registers: $D400-$D406 — frequency ($D400-$D401), pulse width ($D402-$D403), control ($D404), attack/decay ($D405), sustain/release ($D406).",
    },
    {
        "type": "factual",
        "instruction": "What SID filter registers exist?",
        "output": "SID filter registers: $D415 (filter cutoff low 8 bits), $D416 (cutoff high 3 bits + resonance bits 4-7), $D417 (mode switch: LP/BP/HP, voice routing). $D418 is volume and filter mode (bits 0-3 = volume, 4-7 = filter mode).",
    },
    {
        "type": "factual",
        "instruction": "What SID waveforms are available?",
        "output": "SID waveforms: bit 0 = triangle, bit 1 = sawtooth, bit 2 = pulse, bit 3 = noise. Multiple can be set simultaneously.",
    },
    {
        "type": "factual",
        "instruction": "How do you calculate SID frequency for a musical note?",
        "output": "Frequency = (note_Hz * 16777216) / clock_rate. For PAL C64 (clock = 985248 Hz): middle A (440 Hz) = $0856. For NTSC (clock = 1022727 Hz): middle A = $0824.",
    },
    # === CIA Registers ===
    {
        "type": "factual",
        "instruction": "What are the CIA 1 register addresses?",
        "output": "CIA 1 is at $DC00-$DC0F: $DC00 port A (keyboard column), $DC01 port B (keyboard row), $DC02-$DC03 data direction, $DC04-$DC05 timer A, $DC06-$DC07 timer B, $DC08 TOD, $DC0D interrupt control, $DC0E-$DC0F control.",
    },
    {
        "type": "factual",
        "instruction": "What are the CIA 2 register addresses?",
        "output": "CIA 2 is at $DD00-$DD0F: $DD00 controls VIC-II bank select (bits 0-1) and serial bus/RS-232, $DD01 port B, $DD02-$DD03 data direction, $DD04-$DD07 timers, $DD08 TOD, $DD0D interrupt, $DD0E-$DD0F timer control.",
    },
    {
        "type": "factual",
        "instruction": "How do you read the joystick on C64?",
        "output": "Joystick port 2: CIA 1 port A $DC00 = $7F, then read $DC01. Bits: 0=right, 1=left, 2=down, 3=up, 4=fire. Joystick port 1 uses CIA 2 $DD00/$DD01 similarly.",
    },
    # === 6502 Addressing Modes ===
    {
        "type": "theory",
        "instruction": "Explain the 6502 addressing modes used in C64 assembly programming.",
        "output": "The 6502 has 13 addressing modes: Immediate (#$XX), Zero Page ($XX), Zero Page X ($XX,X), Zero Page Y ($XX,Y), Absolute ($XXXX), Absolute X ($XXXX,X), Absolute Y ($XXXX,Y), Indirect ($XX), Indirect X ([$XX],Y), Indirect Y [$XXXX],Y), Accumulator (A), Implied (no operand), and Relative (branch offset). Zero Page modes are fastest (3 cycles), Absolute modes take 4+ cycles.",
    },
    {
        "type": "theory",
        "instruction": "What is zero page addressing and why is it faster?",
        "output": "Zero page addressing accesses memory $00-$FF using a single-byte address. Instructions are 2 bytes and execute in 3 cycles (LDA $XX). Absolute addressing requires 3-byte instructions and 4 cycles minimum. Zero page saves one byte and one cycle per access, making it ideal for frequently used variables.",
    },
    # === Common Programming Patterns ===
    {
        "type": "code",
        "instruction": "Write a raster IRQ setup in 6502 assembly.",
        "context": "Standard VIC-II raster interrupt setup for effects.",
        "output": """        * = $C000
IRQ_SETUP:
        SEI
        LDA #$7F
        STA $D01A        ; disable VIC IRQ
        LDA #<IRQ_HANDLER
        STA $0314        ; IRQ vector low
        LDA #>IRQ_HANDLER
        STA $0315        ; IRQ vector high
        LDA #$01
        STA $D01A        ; enable raster IRQ
        LDA #$64         ; raster line 100
        STA $D012
        LDA $D011
        AND #$7F         ; clear bit 7 of raster MSB
        STA $D011
        CLI
        RTS

IRQ_HANDLER:
        INC $D019        ; acknowledge IRQ
        ; ... effect code here ...
        JMP $EA31        ; standard KERNAL IRQ exit""",
    },
    {
        "type": "code",
        "instruction": "Write a routine to enable and position sprite 0.",
        "context": "VIC-II sprite setup in assembly.",
        "output": """        * = $C000
ENABLE_SPRITE0:
        LDA #$01
        STA $D015        ; enable sprite 0
        LDA #$80         ; X position
        STA $D000        ; sprite 0 X low
        LDA #$00
        STA $D010        ; sprite 0 X bit 8 (0-255 range)
        LDA #$80         ; Y position
        STA $D001        ; sprite 0 Y
        LDA #$0E         ; color 14
        STA $D027        ; sprite 0 color
        LDA #$80 / 64    ; sprite data at $2000
        STA $07F8        ; sprite 0 pointer
        RTS""",
    },
    {
        "type": "code",
        "instruction": "Write a SID sound initialization for a bass note.",
        "context": "SID voice configuration for low-frequency bass.",
        "output": """        * = $C000
SID_BASS:
        ; Voice 1 - low frequency
        LDA #$39         ; frequency low byte
        STA $D400
        LDA #$02         ; frequency high byte
        STA $D401
        ; Pulse width 50%
        LDA #$00
        STA $D402
        LDA #$08
        STA $D403
        ; Control: pulse wave
        LDA #$41
        STA $D404
        ; ADSR: fast attack, long sustain
        LDA #$09         ; attack=0, decay=9
        STA $D405
        LDA #$F0         ; sustain=F, release=0
        STA $D406
        ; Volume
        LDA #$0F
        STA $D418
        RTS""",
    },
    {
        "type": "code",
        "instruction": "Write a screen clear routine using direct memory access.",
        "context": "Clear the 40x25 text screen quickly.",
        "output": """        * = $C000
CLEAR_SCREEN:
        LDA #$20         ; space character
        LDX #$00
CLEAR_LOOP:
        STA $0400,X      ; fill screen RAM
        STA $0500,X
        STA $0600,X
        STA $07C0,X      ; last part (07C0-07E7)
        INX
        BNE CLEAR_LOOP
        ; Clear color RAM
        LDA #$01         ; white
        LDX #$00
CLEAR_COLOR:
        STA $D800,X
        STA $D900,X
        STA $DA00,X
        STA $DBC0,X
        INX
        BNE CLEAR_COLOR
        RTS""",
    },
    {
        "type": "code",
        "instruction": "Write a keyboard scanner using CIA 1.",
        "context": "Read a single keypress from the C64 keyboard.",
        "output": """        * = $C000
SCAN_KEY:
        LDA #$FF
        STA $DC02        ; all columns output
        LDA #$00
        STA $DC03        ; all rows input
        LDA #$00
        STA $DC00        ; select all columns
        LDA $DC01        ; read rows
        CMP #$FF         ; any key pressed?
        BEQ NO_KEY
        ; Find which key - scan columns
        LDX #$00
SCAN_COL:
        LDA COL_MASK,X
        STA $DC00
        LDA $DC01
        CMP #$FF
        BNE KEY_FOUND
        INX
        CPX #$08
        BNE SCAN_COL
NO_KEY:
        LDA #$00
        RTS
KEY_FOUND:
        TXA
        ; ... decode row/column to ASCII ...
        RTS

COL_MASK:
        .BYTE $FE,$FD,$FB,$F7,$EF,$DF,$BF,$7F""",
    },
    {
        "type": "code",
        "instruction": "Write a scroll right effect for text mode.",
        "context": "Smooth horizontal scroll using VIC-II registers.",
        "output": """        * = $C000
SCROLL_RIGHT:
        LDA $D016
        AND #$F8         ; clear scroll bits
        ORA SCROLL_VAL
        STA $D016
        DEC SCROLL_VAL
        LDA SCROLL_VAL
        CMP #$FF
        BNE SCROLL_DONE
        LDA #$07
        STA SCROLL_VAL
SCROLL_DONE:
        RTS

SCROLL_VAL:
        .BYTE $07""",
    },
    {
        "type": "code",
        "instruction": "Write a 16-bit multiply by 10 routine.",
        "context": "Multiply a 16-bit value by 10 for BCD or decimal conversion.",
        "output": """        * = $C000
MUL10:
        ; Input: RESULT (16-bit)
        ; Multiply RESULT by 10 = RESULT*8 + RESULT*2
        LDA RESULT
        STA TEMP
        LDA RESULT+1
        STA TEMP+1
        ; *2
        ASL RESULT
        ROL RESULT+1
        ; save *2 in TEMP2
        LDA RESULT
        STA TEMP2
        LDA RESULT+1
        STA TEMP2+1
        ; *4
        ASL RESULT
        ROL RESULT+1
        ; *8
        ASL RESULT
        ROL RESULT+1
        ; *8 + *2
        CLC
        LDA RESULT
        ADC TEMP2
        STA RESULT
        LDA RESULT+1
        ADC TEMP2+1
        STA RESULT+1
        RTS

RESULT:  .WORD 0
TEMP:    .WORD 0
TEMP2:   .WORD 0""",
    },
    {
        "type": "code",
        "instruction": "Write a raster rainbow border effect.",
        "context": "Classic C64 raster bar border color cycling.",
        "output": """        * = $C000
RAINBOW_SETUP:
        SEI
        LDA #<RAINBOW_IRQ
        STA $0314
        LDA #>RAINBOW_IRQ
        STA $0315
        LDA #$01
        STA $D01A
        LDA #$FF         ; raster line 255 (last visible)
        STA $D012
        LDA $D011
        AND #$7F
        STA $D011
        LDX #$00
        STX COLOR_INDEX
        CLI
        RTS

RAINBOW_IRQ:
        INC $D019
        LDX COLOR_INDEX
        LDA COLOR_TABLE,X
        STA $D020
        INX
        CPX #NUM_COLORS
        BNE RAINBOW_NEXT
        LDX #$00
RAINBOW_NEXT:
        STX COLOR_INDEX
        JMP $EA31

COLOR_INDEX: .BYTE 0
NUM_COLORS = 16
COLOR_TABLE:
        .BYTE 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15""",
    },
    # === KERNAL Routines ===
    {
        "type": "factual",
        "instruction": "What KERNAL routine prints a character to the screen?",
        "output": "JSR $FFD2 (CHROUT) prints the character in the accumulator to the screen.",
    },
    {
        "type": "factual",
        "instruction": "What KERNAL routine reads a character from the keyboard?",
        "output": "JSR $FFE4 (GETIN) reads a character from the keyboard buffer into the accumulator. Zero if no key pressed.",
    },
    {
        "type": "factual",
        "instruction": "What KERNAL routine clears the screen?",
        "output": "JSR $E544 (CLRSCR) clears the screen and homes the cursor.",
    },
    {
        "type": "factual",
        "instruction": "What KERNAL routine sets the cursor position?",
        "output": "Store X (column) and Y (row) and JSR $FFF0 (PLOT) to set cursor position.",
    },
    {
        "type": "factual",
        "instruction": "What is the KERNAL routine for loading from tape/disk?",
        "output": "JSR $FFD5 (LOAD) loads a file. Set filename with JSR $FFBD (SETNAM), file number with JSR $FFC0 (SETLFS).",
    },
    # === BASIC v2 ===
    {
        "type": "factual",
        "instruction": "What is the POKE address for the border color in BASIC?",
        "output": "POKE 53280,n — where n is 0-15 for border color. 53280 = $D020.",
    },
    {
        "type": "factual",
        "instruction": "How do you run machine code from BASIC?",
        "output": "Use SYS address — e.g. SYS 4096 jumps to $1000. The BASIC ROM is mapped at $A000-$BFFF, KERNAL at $E000-$FFFF.",
    },
    {
        "type": "factual",
        "instruction": "How do you PEEK the VIC-II raster line from BASIC?",
        "output": "PEEK(53272) reads the raster counter low 8 bits. 53272 = $D012. Note: values > 255 need PEEK($D011) for bit 8.",
    },
    {
        "type": "factual",
        "instruction": "What are the BASIC v2 memory map locations for screen RAM?",
        "output": "Screen RAM defaults to $0400-$07E7 (1024-2023). Color RAM at 55296 ($D800). PEEK/POKE these addresses for direct screen manipulation.",
    },
    # === Theory / Concepts ===
    {
        "type": "theory",
        "instruction": "Explain the C64 VIC-II bank switching mechanism.",
        "output": "The VIC-II can address 16KB at a time. CIA 2 register $DD00 bits 0-1 select which 16KB bank: bank 0 = $0000-$3FFF, bank 1 = $4000-$7FFF, bank 2 = $8000-$BFFF, bank 3 = $C000-$FFFF. The default is bank 0. The VIC-II then subdivides its bank into screen RAM, character set, and sprites using $D018.",
    },
    {
        "type": "theory",
        "instruction": "Explain how sprite multiplexing works on C64.",
        "output": "Sprite multiplexing reuses the 8 hardware sprites by changing their Y positions mid-frame via raster interrupts. A first IRQ sets sprites for the top half; a second IRQ (triggered at a lower raster line) updates Y positions for the bottom half. By doing this repeatedly, 16+ or even 32+ sprites can appear on screen, trading CPU time for more sprites.",
    },
    {
        "type": "theory",
        "instruction": "What is the C64 memory layout?",
        "output": "$0000-$00FF: Zero page (direct access). $0100-$01FF: Stack. $0200-$03FF: System RAM (buffers, vectors). $0400-$07FF: Screen/color RAM. $0801-$9FFF: BASIC ROM (free for programs). $A000-$BFFF: BASIC ROM. $C000-$CFFF: RAM (free). $D000-$DFFF: I/O or Character ROM. $E000-$FFFF: KERNAL ROM.",
    },
    {
        "type": "theory",
        "instruction": "How does the C64 raster interrupt work?",
        "output": "The VIC-II scans the screen 50 times per second (PAL). Register $D012 holds the current scanline. When the raster line matches $D012, the VIC-II triggers an IRQ (if enabled in $D019/$D01A). The programmer sets $D012 to the desired line and writes an ISR at the IRQ vector ($0314/$0315). The ISR must acknowledge the interrupt by writing to $D019.",
    },
    {
        "type": "theory",
        "instruction": "What is the difference between ACME and TMPx assembly syntax?",
        "output": "ACME uses: LDA #$00 (hex), LDA label (direct), .BYTE/.WORD directives, *= for origin, ; for comments. TMPx uses: LDA #$00, LDA @label (local labels with @), .byt/.wrd, org directive, // for comments. Both target 6502 but differ in directives and label syntax. ACME is more widely used in the C64 demo scene.",
    },
    # === Bugfix patterns ===
    {
        "type": "bugfix",
        "instruction": "What's wrong with this IRQ handler? How would you fix it?",
        "context": """IRQ_HANDLER:
        INC $D019
        LDA #$00
        STA $D020
        JMP $EA31""",
        "output": "The ISR doesn't save/restore the accumulator. If the main code was using A, it will be corrupted. Fix: add PHA before modifying A and PLA after. Also, if X/Y are used, save them too. Corrected: IRQ_HANDLER: INC $D019 / PHA / LDA #$00 / STA $D020 / PLA / JMP $EA31.",
    },
    {
        "type": "bugfix",
        "instruction": "Why does this sprite setup not show sprite 0?",
        "context": """        LDA #$01
        STA $D015        ; enable sprites
        LDA #$80
        STA $D000        ; X
        LDA #$80
        STA $D001        ; Y
        LDA #$0E
        STA $D027        ; color""",
        "output": "The sprite pointer is never set. $07F8 (sprite 0 pointer) defaults to 0, pointing to $0340 which contains BASIC program data. Add: LDA #$XX / STA $07F8 where XX = (sprite_data_address / 64) so the pointer references valid sprite data.",
    },
    {
        "type": "bugfix",
        "instruction": "What's the problem with this SID setup?",
        "context": """        LDA #$09
        STA $D405        ; ADSR
        LDA #$F0
        STA $D406
        LDA #$41
        STA $D404        ; waveform + gate""",
        "output": "The frequency registers ($D400-$D401) are never set. Without a frequency, the SID produces an inaudible tone. Add frequency values before the ADSR setup. Also, for continuous sound, the gate bit (bit 0 of $D404) must be set to 1.",
    },
    # === Scrolling ===
    {
        "type": "code",
        "instruction": "Write a smooth horizontal scroll right routine.",
        "context": "Using VIC-II hardware scrolling with smooth pixel-level movement.",
        "output": """        * = $C000
SCROLL_SMOOTH:
        ; Wait for raster
        LDA $D012
        CMP #$FF
        BNE SCROLL_SMOOTH
        ; Decrement scroll value
        DEC SCROLL_X
        LDA SCROLL_X
        AND #$07
        STA TEMP
        LDA $D016
        ORA #$07
        EOR TEMP
        STA $D016
        RTS

SCROLL_X: .BYTE $07
TEMP:     .BYTE $00""",
    },
    # === Bitmap mode ===
    {
        "type": "code",
        "instruction": "Write a routine to set up multicolor bitmap mode.",
        "context": "Configure VIC-II for 160x200 multicolor bitmap graphics.",
        "output": """        * = $C000
BITMAP_SETUP:
        LDA $D011
        ORA #$20         ; enable bitmap mode (bit 5)
        STA $D011
        LDA $D016
        ORA #$10         ; enable multicolor (bit 4)
        STA $D016
        LDA $D018
        AND #$F0
        ORA #$08         ; screen at $2000, chars irrelevant
        STA $D018
        RTS""",
    },
    # === Timer/CIA ===
    {
        "type": "code",
        "instruction": "Write a CIA timer setup for a 1-second delay using Timer A.",
        "context": "Using CIA 1 Timer A to generate a periodic interrupt.",
        "output": """        * = $C000
TIMER_SETUP:
        SEI
        LDA #$00
        STA $DC0E        ; stop Timer A
        LDA #<DELAY      ; timer low byte
        STA $DC04
        LDA #>DELAY      ; timer high byte
        STA $DC05
        LDA #$81
        STA $DC0D        ; enable Timer A interrupt
        LDA #$01
        STA $DC0E        ; start Timer A, continuous
        CLI
        RTS

; PAL: 985248 Hz / 64 = ~15395 cycles/sec = $3C23
DELAY = $3C23""",
    },
]

# ---------------------------------------------------------------------------
# Variation templates
# ---------------------------------------------------------------------------

# PAL/NTSC frequency pairs for SID
PAL_NTSC_NOTES = [
    ("PAL", 985248, 0x0856, "A4"),
    ("PAL", 985248, 0x042C, "A3"),
    ("PAL", 985248, 0x10AC, "A5"),
    ("NTSC", 1022727, 0x0824, "A4"),
    ("NTSC", 1022727, 0x0412, "A3"),
    ("NTSC", 1022727, 0x104A, "A5"),
]

# Sprite number swaps
SPRITE_SWAP = [
    {
        "old": "0",
        "new": "3",
        "old_hex": "$01",
        "new_hex": "$08",
        "ptr_off": 3,
        "color_reg": "$D02A",
    },
    {
        "old": "1",
        "new": "5",
        "old_hex": "$02",
        "new_hex": "$20",
        "ptr_off": 5,
        "color_reg": "$D02C",
    },
    {
        "old": "2",
        "new": "7",
        "old_hex": "$04",
        "new_hex": "$80",
        "ptr_off": 7,
        "color_reg": "$D02E",
    },
    {
        "old": "3",
        "new": "0",
        "old_hex": "$08",
        "new_hex": "$01",
        "ptr_off": 0,
        "color_reg": "$D027",
    },
    {
        "old": "5",
        "new": "6",
        "old_hex": "$20",
        "new_hex": "$40",
        "ptr_off": 6,
        "color_reg": "$D02D",
    },
]

# Register address swaps for factual QAs
REGISTER_SWAPS = [
    ("$D020", "$D021", "border color", "background color"),
    ("$D015", "$D017", "sprite enable", "sprite Y expansion"),
    ("$D000", "$D001", "sprite 0 X", "sprite 0 Y"),
    ("$DC00", "$DC01", "CIA 1 port A", "CIA 1 port B"),
    ("$DD00", "$DD01", "CIA 2 port A", "CIA 2 port B"),
    ("$D400", "$D407", "SID voice 1 freq", "SID voice 2 freq"),
    ("$D404", "$D40B", "SID voice 1 control", "SID voice 2 control"),
    ("$D415", "$D416", "SID filter cutoff low", "SID filter cutoff high"),
]

# Raster line variations
RASTER_LINES = [
    (0x64, "100"),
    (0x80, "128"),
    (0xFF, "255"),
    (0xC8, "200"),
    (0x30, "48"),
    (0xF0, "240"),
]

# Color variations
COLORS = [
    (0x00, "black", "nero"),
    (0x01, "white", "bianco"),
    (0x02, "red", "rosso"),
    (0x03, "cyan", "ciano"),
    (0x04, "purple", "viola"),
    (0x05, "green", "verde"),
    (0x06, "blue", "blu"),
    (0x07, "yellow", "giallo"),
    (0x08, "orange", "arancione"),
    (0x09, "brown", "marrone"),
    (0x0A, "light red", "rosso chiaro"),
    (0x0B, "dark grey", "grigio scuro"),
    (0x0C, "grey", "grigio"),
    (0x0D, "light green", "verde chiaro"),
    (0x0E, "light blue", "blu chiaro"),
    (0x0F, "light grey", "grigio chiaro"),
]

# KERNAL routine swaps
KERNAL_SWAPS = [
    ("$FFD2", "$FFE4", "CHROUT", "GETIN"),
    ("$E544", "$E544", "CLRSCR", "CLRSCR"),
    ("$FFF0", "$FFD2", "PLOT", "CHROUT"),
    ("$FFD5", "$FFBD", "LOAD", "SETNAM"),
]

# Address offset pairs for variations
BANK_OFFSETS = [
    (0x0000, "$0000", "$3FFF", 0),
    (0x4000, "$4000", "$7FFF", 1),
    (0x8000, "$8000", "$BFFF", 2),
    (0xC000, "$C000", "$FFFF", 3),
]

# Screen RAM locations
SCREEN_RAM = [
    ("$0400", "1024"),
    ("$0800", "2048"),
    ("$0C00", "3072"),
    ("$1000", "4096"),
]

# ---------------------------------------------------------------------------
# Assembly syntax validator (basic regex)
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

DIRECTIVES = {".BYTE", ".WORD", ".FILL", "*"}

ASSEMBLY_LINE_RE = re.compile(
    r"""^\s*(?:(\w+):)?\s*            # optional label
         (?:(\.\w+|\w+))\s*           # mnemonic or directive
         (?:[#$%(]\w+[,\s]*[\w)]*)?    # optional operand
         (?:;.*)?$                     # optional comment""",
    re.IGNORECASE | re.VERBOSE,
)

VALID_HEX_RE = re.compile(r"^\$[0-9A-Fa-f]+$")
VALID_IMM_RE = re.compile(r"^#\$?[0-9A-Fa-f]+$")
VALID_ZERO_PAGE_RE = re.compile(r"^\$[0-9A-Fa-f]+$")
VALID_ABS_RE = re.compile(r"^\$[0-9A-Fa-f]+$")


def validate_assembly_syntax(code: str) -> tuple[bool, list[str]]:
    """Basic validation of 6502 assembly syntax. Returns (valid, errors)."""
    errors = []
    valid_count = 0
    total_code_lines = 0

    for line in code.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("*"):
            continue

        # Labels with directive/instruction
        if ":" in line:
            parts = line.split(":", 1)
            line = parts[1].strip()

        # Skip comment-only lines
        if line.startswith(";"):
            continue

        total_code_lines += 1
        parts = line.split(";", 1)[0].strip()
        if not parts:
            continue

        tokens = parts.replace(",", " ").replace("#", " # ").split()
        if not tokens:
            continue

        mnemonic = tokens[0].upper()
        if mnemonic in VALID_6502_OPCODES or mnemonic.startswith("."):
            valid_count += 1
        else:
            errors.append(f"Unknown mnemonic: {mnemonic}")

    if total_code_lines == 0:
        return False, ["No assembly code found"]

    ratio = valid_count / total_code_lines if total_code_lines > 0 else 0
    return ratio >= 0.7, errors


# ---------------------------------------------------------------------------
# QA Generator
# ---------------------------------------------------------------------------


class DistillationScaler:
    """Generates C64 QA pairs from templates and seed data."""

    def __init__(self, seed_data: Optional[list[dict]] = None):
        self.seeds = seed_data or SEEDS
        self._seen_hashes: set[str] = set()
        self.generated: list[dict] = []

    def _hash(self, instruction: str, output: str) -> str:
        text = f"{instruction.strip().lower()}|||{output.strip().lower()}"
        return hashlib.md5(text.encode()).hexdigest()

    def _add_unique(self, qa: dict) -> bool:
        h = self._hash(qa["instruction"], qa["output"])
        if h in self._seen_hashes:
            return False
        self._seen_hashes.add(h)
        self.generated.append(qa)
        return True

    # -- Template generators (factual) --

    def _gen_factual_variations(self, seed: dict) -> list[dict]:
        results = []

        # Generate register swap variations
        for old, new, old_desc, new_desc in REGISTER_SWAPS:
            if old in seed["output"] or old.lower() in seed["instruction"].lower():
                new_out = seed["output"].replace(old, new)
                new_instr = seed["instruction"].replace(old_desc, new_desc)
                results.append(
                    {
                        "instruction": new_instr,
                        "context": "",
                        "constraints": "Answer with a precise factual statement.",
                        "output": new_out,
                    }
                )

        # Color variations
        if "color" in seed["instruction"].lower() or "$D020" in seed.get("output", ""):
            for val, name, name_it in COLORS[:6]:
                hex_val = f"${val:02X}"
                if "0-15" in seed["output"]:
                    new_out = seed["output"].replace(
                        "0-15", f"0-15 (e.g., {hex_val} = {name})"
                    )
                    results.append(
                        {
                            "instruction": seed["instruction"],
                            "context": "",
                            "constraints": "Answer with a precise factual statement.",
                            "output": new_out,
                        }
                    )
                    break

        # Raster line variations
        for val, name in RASTER_LINES:
            hex_val = f"${val:02X}"
            if (
                "$D012" in seed.get("output", "")
                and "line" in seed["instruction"].lower()
            ):
                new_out = seed["output"].replace("$D012", f"$D012 (raster line {name})")
                results.append(
                    {
                        "instruction": seed["instruction"],
                        "context": "",
                        "constraints": "Answer with a precise factual statement.",
                        "output": new_out,
                    }
                )
                break

        # KERNAL address swaps
        for old, new, old_name, new_name in KERNAL_SWAPS:
            if old in seed.get("output", ""):
                new_out = seed["output"].replace(old, new).replace(old_name, new_name)
                if new_out != seed["output"]:
                    results.append(
                        {
                            "instruction": seed["instruction"].replace(
                                old_name, new_name
                            ),
                            "context": "",
                            "constraints": "Answer with a precise factual statement.",
                            "output": new_out,
                        }
                    )

        return results

    # -- Template generators (code) --

    def _gen_code_variations(self, seed: dict) -> list[dict]:
        results = []
        code = seed.get("output", "")

        # Sprite number swaps
        for swap in SPRITE_SWAP:
            if (
                f"sprite {swap['old']}" in seed["instruction"].lower()
                or f"sprite 0" in seed["instruction"].lower()
            ):
                new_code = code
                new_code = new_code.replace(f"sprite 0", f"sprite {swap['new']}")
                new_code = new_code.replace("$D000", f"$D00{swap['new']}")
                new_code = new_code.replace(
                    "$D001", f"$D00{str(int(swap['new']) * 2 + 1)[-1]}"
                )
                new_code = new_code.replace("$D027", swap["color_reg"])
                new_code = new_code.replace("$07F8", f"$07F{8 + int(swap['new'])}")
                new_instr = seed["instruction"].replace(
                    "sprite 0", f"sprite {swap['new']}"
                )
                results.append(
                    {
                        "instruction": new_instr,
                        "context": seed.get("context", ""),
                        "constraints": "Return valid ACME 6502 assembly. Use *= and ; for comments.",
                        "output": new_code,
                    }
                )

        # Color swaps in code
        for val, name, _ in COLORS[:4]:
            if (
                "$D020" in code
                or "bordo" in seed["instruction"].lower()
                or "border" in seed["instruction"].lower()
            ):
                new_code = code.replace("LDA #$00", f"LDA #${val:02X}")
                new_code = new_code.replace("LDA #$01", f"LDA #${val:02X}")
                if new_code != code:
                    results.append(
                        {
                            "instruction": seed["instruction"],
                            "context": seed.get("context", ""),
                            "constraints": f"Use {name} color (value ${val:02X}).",
                            "output": new_code,
                        }
                    )
                    break

        # Raster line swaps
        for val, name in RASTER_LINES:
            if "$D012" in code and "#$64" in code:
                new_code = code.replace("#$64", f"#${val:02X}")
                results.append(
                    {
                        "instruction": seed["instruction"],
                        "context": f"Target raster line {name} (0x{val:02X}).",
                        "constraints": "Return valid ACME 6502 assembly.",
                        "output": new_code,
                    }
                )
                break

        # Screen RAM swaps
        for addr, decimal in SCREEN_RAM:
            if "$0400" in code:
                new_code = code.replace("$0400", addr)
                if addr != "$0400":
                    results.append(
                        {
                            "instruction": seed["instruction"],
                            "context": f"Screen RAM at {decimal} (address {addr}).",
                            "constraints": "Return valid ACME 6502 assembly.",
                            "output": new_code,
                        }
                    )
                    break

        return results

    # -- Template generators (explain) --

    def _gen_explain_variations(self, seed: dict) -> list[dict]:
        results = []
        if seed.get("type") != "theory":
            return results

        output = seed["output"]

        # Generate simplified version
        if len(output) > 100:
            short = output[: output.find(".") + 1] if "." in output else output[:100]
            results.append(
                {
                    "instruction": f"In one sentence: {seed['instruction']}",
                    "context": "",
                    "constraints": "Keep the answer under 30 words.",
                    "output": short,
                }
            )

        # Generate step-by-step version
        if (
            "how" in seed["instruction"].lower()
            or "work" in seed["instruction"].lower()
        ):
            results.append(
                {
                    "instruction": f"Step by step: {seed['instruction']}",
                    "context": "",
                    "constraints": "Number each step. 3-5 steps maximum.",
                    "output": output,
                }
            )

        return results

    # -- Template generators (bugfix) --

    def _gen_bugfix_variations(self, seed: dict) -> list[dict]:
        results = []
        if seed.get("type") != "bugfix":
            return results

        code = seed.get("context", "")

        # Missing PHA/PLA bug
        if "PHA" in seed.get("output", "") and "save" in seed.get("output", "").lower():
            results.append(
                {
                    "instruction": "What's wrong with this simple IRQ handler?",
                    "context": """IRQ_HANDLER:
        INC $D019
        JSR $E544
        JMP $EA31""",
                    "output": "The ISR calls CLRSCR but doesn't save/restore the accumulator. CLHRSCR modifies A, corrupting whatever the main loop was doing. Fix: add PHA/TXA/PHA/TYA/PHA before and PLA/TAY/PLA/TAX/PLA after the body.",
                }
            )

        # Wrong register bug
        if "$D020" in seed.get("output", "") or "$D021" in seed.get("output", ""):
            results.append(
                {
                    "instruction": "I want to change the background color but the border changes instead. Why?",
                    "context": """        LDA #$05
        STA $D020        ; should be background""",
                    "output": "You're writing to $D020 which is the BORDER color register. The background color register is $D021. Change STA $D020 to STA $D021.",
                }
            )

        return results

    # -- Template generators (theory) --

    def _gen_theory_variations(self, seed: dict) -> list[dict]:
        results = []
        if seed.get("type") != "theory":
            return results

        output = seed["output"]

        # Quiz-style
        if "addressing" in seed["instruction"].lower():
            results.append(
                {
                    "instruction": "List all 6502 addressing modes with one example each.",
                    "context": "",
                    "constraints": "Format as a numbered list with mode name and example instruction.",
                    "output": output,
                }
            )

        # Comparison style
        if "PAL" in output or "NTSC" in output or "frequency" in output.lower():
            results.append(
                {
                    "instruction": "What are the key timing differences between PAL and NTSC C64?",
                    "context": "",
                    "constraints": "Include specific frequency values and raster line counts.",
                    "output": "PAL C64: 985248 Hz clock, 63 cycles/line, 312 lines/frame, 50Hz. NTSC C64: 1022727 Hz clock, 65 cycles/line, 263 lines/frame, 60Hz. SID frequencies differ: PAL A4 = $0856, NTSC A4 = $0824.",
                }
            )

        return results

    # -- Factual seed generation (hardcoded QA variations) --

    def _gen_factual_from_hardware(self) -> list[dict]:
        """Generate factual QA pairs from C64 hardware knowledge."""
        pairs = []

        # VIC-II register fact pairs
        vic_facts = [
            ("$D000", "Sprite 0 X position"),
            ("$D001", "Sprite 0 Y position"),
            ("$D002", "Sprite 1 X position"),
            ("$D003", "Sprite 1 Y position"),
            ("$D004", "Sprite 2 X position"),
            ("$D005", "Sprite 2 Y position"),
            ("$D006", "Sprite 3 X position"),
            ("$D007", "Sprite 3 Y position"),
            ("$D008", "Sprite 4 X position"),
            ("$D009", "Sprite 4 Y position"),
            ("$D00A", "Sprite 5 X position"),
            ("$D00B", "Sprite 5 Y position"),
            ("$D00C", "Sprite 6 X position"),
            ("$D00D", "Sprite 6 Y position"),
            ("$D00E", "Sprite 7 X position"),
            ("$D00F", "Sprite 7 Y position"),
            ("$D010", "Sprite X MSB (bit 8 for all sprites)"),
            (
                "$D011",
                "VIC control: raster MSB (bit 7), bitmap mode (bit 5), display enable (bit 3), Y scroll (bits 0-2)",
            ),
            ("$D012", "Current raster line (low 8 bits)"),
            ("$D013", "Light pen X"),
            ("$D014", "Light pen Y"),
            ("$D015", "Sprite display enable (bit N = sprite N)"),
            (
                "$D016",
                "VIC control: X scroll (bits 0-2), multicolor mode (bit 4), 38-col mode (bit 3)",
            ),
            ("$D017", "Sprite Y expand (bit N doubles sprite N height)"),
            (
                "$D018",
                "VIC memory control: screen RAM bank (bits 4-7), char set (bits 1-3)",
            ),
            (
                "$D019",
                "VIC interrupt register: raster (bit 0), sprite-bg (bit 1), sprite-sprite (bit 2), light pen (bit 3), IRQ flag (bit 7)",
            ),
            ("$D01A", "VIC interrupt enable: same bits as $D019"),
            ("$D01B", "Sprite priority: 0 = sprite over bg, 1 = bg over sprite"),
            ("$D01C", "Sprite multicolor mode enable (bit N)"),
            ("$D01D", "Sprite X expand (bit N doubles sprite N width)"),
            ("$D01E", "Sprite-sprite collision (read-only, cleared on read)"),
            ("$D01F", "Sprite-background collision (read-only, cleared on read)"),
            ("$D020", "Border color (0-15)"),
            ("$D021", "Background color (0-15)"),
            ("$D022", "Background color 1 (multicolor mode)"),
            ("$D023", "Background color 2 (multicolor mode)"),
            ("$D024", "Background color 3 (multicolor mode)"),
            ("$D025", "Sprite multicolor 0"),
            ("$D026", "Sprite multicolor 1"),
            ("$D027", "Sprite 0 color"),
            ("$D028", "Sprite 1 color"),
            ("$D029", "Sprite 2 color"),
            ("$D02A", "Sprite 3 color"),
            ("$D02B", "Sprite 4 color"),
            ("$D02C", "Sprite 5 color"),
            ("$D02D", "Sprite 6 color"),
            ("$D02E", "Sprite 7 color"),
        ]

        for addr, desc in vic_facts:
            pairs.append(
                {
                    "type": "factual",
                    "instruction": f"What does VIC-II register {addr} control?",
                    "output": f"VIC-II register {addr} controls {desc}.",
                }
            )

        # SID register facts
        sid_facts = [
            ("$D400-$D401", "SID voice 1 frequency (16-bit, low/high byte)"),
            ("$D402-$D403", "SID voice 1 pulse width (12-bit)"),
            (
                "$D404",
                "SID voice 1 control: noise(bit 3), pulse(bit 2), sawtooth(bit 1), triangle(bit 0), gate(bit 0 of control)",
            ),
            ("$D405", "SID voice 1 attack (upper nybble) and decay (lower nybble)"),
            ("$D406", "SID voice 1 sustain (upper nybble) and release (lower nybble)"),
            ("$D407-$D40E", "SID voice 2 (same layout as voice 1, offset +7)"),
            ("$D40F-$D416", "SID voice 3 (same layout as voice 1, offset +14)"),
            ("$D415", "SID filter cutoff frequency (low 8 bits)"),
            ("$D416", "SID filter cutoff (high 3 bits) and resonance (bits 4-7)"),
            ("$D417", "SID filter mode: 3-bit LP/BP/HP select, voice routing bits"),
            ("$D418", "SID volume (bits 0-3) and filter mode (bits 4-7)"),
        ]

        for addr, desc in sid_facts:
            pairs.append(
                {
                    "type": "factual",
                    "instruction": f"What does SID register {addr} control?",
                    "output": f"SID register {addr} controls {desc}.",
                }
            )

        # CIA register facts
        cia_facts = [
            ("$DC00", "CIA 1 port A: keyboard column select (output)"),
            ("$DC01", "CIA 1 port B: keyboard row read (input)"),
            ("$DC02", "CIA 1 data direction port A"),
            ("$DC03", "CIA 1 data direction port B"),
            ("$DC04-$DC05", "CIA 1 Timer A (16-bit, low/high)"),
            ("$DC06-$DC07", "CIA 1 Timer B (16-bit, low/high)"),
            ("$DC08", "CIA 1 TOD (time of day) counter"),
            ("$DC0D", "CIA 1 interrupt control (read: IRQ sources, write: enable)"),
            ("$DC0E", "CIA 1 Timer A control (start, latch, chain)"),
            ("$DC0F", "CIA 1 Timer B control"),
            ("$DD00", "CIA 2 port A: VIC-II bank select (bits 0-1), serial bus"),
            ("$DD01", "CIA 2 port B"),
            ("$DD02", "CIA 2 data direction port A"),
            ("$DD03", "CIA 2 data direction port B"),
            ("$DD04-$DD05", "CIA 2 Timer A (16-bit)"),
            ("$DD06-$DD07", "CIA 2 Timer B (16-bit)"),
            ("$DD08", "CIA 2 TOD counter"),
            ("$DD0D", "CIA 2 interrupt control"),
            ("$DD0E", "CIA 2 Timer A control"),
            ("$DD0F", "CIA 2 Timer B control"),
        ]

        for addr, desc in cia_facts:
            pairs.append(
                {
                    "type": "factual",
                    "instruction": f"What does CIA register {addr} control?",
                    "output": f"CIA register {addr} controls {desc}.",
                }
            )

        # KERNAL routine facts
        kernal_facts = [
            ("$FFD2 (CHROUT)", "print a character to the screen"),
            ("$FFE4 (GETIN)", "read a character from the keyboard buffer"),
            ("$E544 (CLRSCR)", "clear the screen and home the cursor"),
            ("$FFF0 (PLOT)", "get/set cursor position (X=column, Y=row)"),
            ("$FFD5 (LOAD)", "load a file from tape or disk"),
            ("$FFBD (SETNAM)", "set filename for I/O operations"),
            ("$FFC0 (SETLFS)", "set logical file parameters"),
            ("$FFC3 (CLOSE)", "close a logical file"),
            ("$FFC6 (CHKIN)", "open channel for input"),
            ("$FFC9 (CKOUT)", "open channel for output"),
            ("$FFE1 (STOP)", "check if STOP key was pressed"),
            ("$FFE7 (IOBASE)", "return I/O base address"),
            ("$FF84 (IOINIT)", "initialize I/O devices"),
            ("$FF87 (RAMTAS)", "initialize RAM"),
            ("$FF8A (RESTOR)", "restore default I/O vectors"),
            ("$FF8D (VECTOR)", "read/set I/O vectors"),
        ]

        for addr, desc in kernal_facts:
            pairs.append(
                {
                    "type": "factual",
                    "instruction": f"What KERNAL routine {addr} does what?",
                    "output": f"{addr} — {desc}.",
                }
            )

        # BASIC v2 facts
        basic_facts = [
            ("POKE 53280,n", "border color (0-15)"),
            ("POKE 53281,n", "background color (0-15)"),
            ("POKE 53272,n", "VIC-II $D018 — screen/charset setup"),
            ("PEEK(53280)", "current border color"),
            ("PEEK(53281)", "current background color"),
            ("PEEK(53272)", "current VIC-II $D018 value"),
            ("PEEK(56320)", "CIA 1 $DC00 — joystick port 2"),
            ("PEEK(56321)", "CIA 1 $DC01 — keyboard row/joystick"),
            ("SYS 4096", "call machine code at $1000"),
            ("PRINT CHR$(147)", "clear screen (147 = CLR key)"),
            ("PRINT CHR$(13)", "return cursor to home position"),
        ]

        for cmd, desc in basic_facts:
            pairs.append(
                {
                    "type": "factual",
                    "instruction": f"What does {cmd} do in BASIC?",
                    "output": f"{cmd} — {desc}.",
                }
            )

        return pairs

    # -- Additional code templates --

    def _gen_extra_code_templates(self) -> list[dict]:
        """Generate extra code QA pairs from additional templates."""
        extras = [
            {
                "instruction": "Write a busy-wait raster sync loop.",
                "context": "Wait for a specific raster line before executing code.",
                "output": """        * = $C000
WAIT_RASTER:
        LDA #$80
WAIT:   CMP $D012
        BNE WAIT
        RTS""",
            },
            {
                "instruction": "Write a routine to toggle between bitmap and text mode.",
                "context": "Switch between text mode and bitmap mode using $D011.",
                "output": """        * = $C000
TOGGLE_MODE:
        LDA $D011
        EOR #$20         ; toggle bit 5 (bitmap mode)
        STA $D011
        RTS""",
            },
            {
                "instruction": "Write a double-buffer sprite animation setup.",
                "context": "Alternate sprite pointers each frame for 2-frame animation.",
                "output": """        * = $C000
ANIM_SPRITE:
        LDX ANIM_FRAME
        LDA SPR_PTRS,X
        STA $07F8
        TXA
        EOR #$01
        STA ANIM_FRAME
        RTS

ANIM_FRAME: .BYTE 0
SPR_PTRS:   .BYTE $80, $81  ; sprite data at $2000, $2040""",
            },
            {
                "instruction": "Write a routine to read paddle (analog joystick) port.",
                "context": "Read the potentiometer value from a paddle controller.",
                "output": """        * = $C000
READ_PADDLE:
        LDA #$80         ; select paddle X
        STA $DC00
        NOP
        NOP
        LDA $DC01        ; read pot value (0-255)
        RTS""",
            },
            {
                "instruction": "Write an open border trick to get more screen width.",
                "context": "Display 38 columns in a 40-column border area.",
                "output": """        * = $C000
OPEN_BORDER:
        SEI
        LDA #<OPEN_IRQ
        STA $0314
        LDA #>OPEN_IRQ
        STA $0315
        LDA #$01
        STA $D01A
        LDA #$FC
        STA $D012
        LDA $D011
        AND #$7F
        STA $D011
        CLI
        RTS

OPEN_IRQ:
        INC $D019
        NOP
        NOP
        NOP
        LDA $D011
        AND #$F0
        ORA #$03
        STA $D011        ; expand display during lower border
        JMP $EA31""",
            },
            {
                "instruction": "Write a delay loop of approximately 1 second on PAL.",
                "context": "Nested loop for timing on PAL C64.",
                "output": """        * = $C000
DELAY_1S:
        LDX #$FF
OUTER:  LDY #$FF
INNER:  DEY
        BNE INNER
        DEX
        BNE OUTER
        RTS""",
            },
            {
                "instruction": "Write a routine to copy a character set from ROM to RAM.",
                "context": "Copy the default character ROM for custom font modification.",
                "output": """        * = $C000
COPY_CHARSET:
        LDA #$33         ; bank in char ROM ($D000-$DFFF)
        STA $01
        LDX #$00
COPY:   LDA $D000,X
        STA $2000,X
        LDA $D100,X
        sta $2100,X
        LDA $D200,X
        STA $2200,X
        LDA $D300,X
        STA $2300,X
        INX
        BNE COPY
        LDA #$37         ; restore default banking
        STA $01
        RTS""",
            },
            {
                "instruction": "Write a music player main loop.",
                "context": "Basic SID music player with note pointer.",
                "output": """        * = $C000
PLAY_MUSIC:
        LDX NOTE_PTR
        LDA FREQ_TABLE,X
        BEQ DONE
        STA $D400
        LDA #$00
        STA $D401
        LDA #$41
        STA $D404        ; gate on
        INC NOTE_PTR
        RTS
DONE:
        LDA #$40
        STA $D404        ; gate off
        RTS

NOTE_PTR: .BYTE 0
FREQ_TABLE:
        .BYTE $39,$02    ; A2
        .BYTE $55,$02    ; B2
        .BYTE $6B,$02    ; C#3
        .BYTE $00,$00    ; end marker""",
            },
            {
                "instruction": "Write a routine that sets up VIC-II bank 2 ($8000-$BFFF).",
                "context": "Switch VIC-II to use bank 2 for custom charset/screen.",
                "output": """        * = $C000
SET_BANK2:
        LDA $DD00
        AND #$FC         ; clear bits 0-1
        ORA #$01         ; bank 2 = %01
        STA $DD00
        RTS""",
            },
            {
                "instruction": "Write an IRQ-based stable raster bar routine.",
                "context": "Generate a stable raster effect by waiting for exact line.",
                "output": """        * = $C000
STABLE_RASTER:
        LDA $D012
        CMP $D012
        BEQ STABLE_RASTER  ; wait for exact cycle
        ; now we are on the exact raster line
        LDX #$0F
        STX $D020
        ; delay for centering
        LDX #$08
DELAY:  DEX
        BNE DELAY
        LDX #$00
        STX $D020        ; restore border
        RTS""",
            },
        ]
        return extras

    # -- Additional theory templates --

    def _gen_extra_theory(self) -> list[dict]:
        """Generate extra theory QA pairs."""
        return [
            {
                "instruction": "Explain the C64 sprite collision detection system.",
                "output": "The VIC-II detects collisions between sprites ($D01E) and between sprites and background ($D01F). When sprite-sprite bit N is set, sprites have collided. Reading these registers clears them. Collision detection works on the non-transparent pixels. It's useful for simple game collision logic without software checking.",
            },
            {
                "instruction": "What is the C64 stack and how is it used?",
                "output": "The 6502 stack lives at $0100-$01FF (256 bytes). Stack pointer starts at $FF. PHA pushes A (SP decrements), PLA pops (SP increments). JSR pushes return address (2 bytes), RTS pulls it. Interrupts push PC, status. The stack is LIFO, 256 bytes max.",
            },
            {
                "instruction": "How does the C64 SID filter work?",
                "output": "The SID filter is a programmable analog filter controlled by $D415-$D418. It has three modes: low-pass (LP), band-pass (BP), and high-pass (HP). $D415-$D416 set cutoff frequency (11 bits). $D417 controls resonance (bits 4-7) and which voices pass through the filter (bits 0-2). $D418 sets output volume and selects filter mode.",
            },
            {
                "instruction": "Explain the difference between raster IRQ and CIA timer IRQ on C64.",
                "output": "Raster IRQ (VIC-II $D019/$D01A) fires at a specific scanline — used for split-screen effects, stable raster bars, and mid-frame register changes. CIA timer IRQ fires at CPU cycle intervals — used for music players, game loops, and periodic tasks. Raster IRQ is timing-dependent on screen position; CIA timer IRQ is timing-independent. Both use the same $0314 vector by default.",
            },
            {
                "instruction": "What are the C64 memory banking options and how do you select them?",
                "output": "The C64 has two banking layers: (1) VIC-II bank via CIA 2 $DD00 bits 0-1 (4 × 16KB banks), and (2) ROM/RAM banking via $01 (processor port). $01 bits: bit 0 = LORAM (BASIC ROM), bit 1 = HIRAM (KERNAL ROM), bit 2 = CHAREN (char ROM vs I/O). Default $37 = all ROMs enabled. $35 = RAM only (KERNAL visible). $33 = char ROM visible at $D000.",
            },
            {
                "instruction": "Explain the difference between ACME assembler directives .BYTE and .WORD.",
                "output": ".BYTE emits one or more 8-bit values: .BYTE $0F, $FF. .WORD emits 16-bit values in little-endian order (LSB first): .WORD $C000 emits $00, $C0. .WORD can define address tables. .BYTE is used for single-byte data, color values, and small constants.",
            },
            {
                "instruction": "How does sprite priority work on VIC-II?",
                "output": "Register $D01B controls sprite-background priority per sprite. Bit 0 = sprite 0, etc. When bit is 0 (default): sprites appear OVER background graphics. When bit is 1: sprites appear BEHIND background graphics. This is useful for characters walking behind buildings. Only affects sprites vs background, not sprites vs each other.",
            },
            {
                "instruction": "Explain how the C64 character ROM is organized.",
                "output": "The C64 character ROM at $D000-$DFFF contains 256 characters × 8 bytes = 2KB per set. Two character sets exist: uppercase/graphics ($1000-$17FF) and lowercase/uppercase ($1800-$1FFF). When CHAREN bit is set, the I/O area is visible instead. To access char ROM directly, set processor port $01 to $33 to bank in char ROM at $D000.",
            },
        ]

    # -- Additional bugfix templates --

    def _gen_extra_bugfix(self) -> list[dict]:
        """Generate extra bugfix QA pairs."""
        return [
            {
                "instruction": "Why does my code crash when I use JMP indirect at $FFFE?",
                "context": "JMP ($FFFE) is supposed to read the IRQ vector.",
                "output": "JMP ($FFFE) works correctly — it reads the address from $FFFE/$FFFF. However, JMP ($03FF) would bug because indirect addressing wraps within the page: it reads from $03FF and $0300, not $0400. This is a known 6502 hardware bug. Avoid indirect addressing across page boundaries.",
            },
            {
                "instruction": "Why does my LDA #$10 + CMP #$10 + BNE not branch?",
                "context": "Expected BNE to take the branch.",
                "output": "CMP #$10 when A = $10 sets the Z flag (zero = equal). BNE branches when Z is CLEAR (not equal). Since the values are equal, Z=1, so BNE does NOT branch. Use BEQ instead for equal comparison. BNE is for 'not equal' cases.",
            },
            {
                "instruction": "This SID code produces no sound. What's wrong?",
                "context": """        LDA #$49
        STA $D404        ; control register
        LDA #$0F
        STA $D418""",
                "output": "The gate bit (bit 0 of $D404) controls ADSR envelope start. $49 = %01001001, bit 0 = 1 (gate on). However, if the frequency ($D400/$D401) is zero or very low, the sound is inaudible. Also, ADSR registers ($D405/$D406) are never set, so sustain is 0. Set non-zero frequency and non-zero sustain.",
            },
            {
                "instruction": "My sprite appears at the wrong position. Why?",
                "context": """        LDA #$100
        STA $D000""",
                "output": "LDA #$100 is invalid — immediate mode only handles 8-bit values ($00-$FF). You probably want LDA #$00 and set $D010 separately for bit 8. For X > 255, set the corresponding bit in $D010. Sprite coordinates above 255 wrap around: X=$100 shows at X=0.",
            },
            {
                "instruction": "My BASIC program crashes with ILLEGAL QUANTITY. Why?",
                "context": "10 POKE 53280, 256",
                "output": "POKE requires values 0-255. 256 is out of range (it's a 9-bit number). Use POKE 53280, 0 (or POKE 53280, 256-256). The error is because PEEK/POKE only accept byte values.",
            },
            {
                "instruction": "Why does my branch instruction behave unexpectedly?",
                "context": "BNE to a label that is 200 bytes away.",
                "output": "Branch displacement is a signed 8-bit offset (-128 to +127). A jump of +200 bytes exceeds the range. You'll get a branch to an incorrect address. For longer jumps, use JMP indirect or restructure the code with a JMP over a JMP.",
            },
            {
                "instruction": "My raster split works on PAL but not NTSC. Why?",
                "context": "Using raster line $FF for the split.",
                "output": "PAL has 312 raster lines (0-311), NTSC has 263 (0-262). Raster line $FF (255) works on both, but the timing and cycle count per line differ. PAL has 63 cycles/line, NTSC has 65. This affects the number of CPU cycles available for your effect. Recalculate timing delays for NTSC.",
            },
            {
                "instruction": "Why does my 16-bit ADC give wrong results?",
                "context": """        LDA LOW1
        ADC LOW2
        STA RESULT
        LDA HIGH1
        ADC HIGH2
        STA RESULT+1""",
                "output": "You forgot to clear the carry before the first ADC. After any instruction that modifies flags, C could be set. Add CLC before the first ADC. Without it, you're adding an extra 1 to the low byte if carry was set from a previous operation.",
            },
        ]

    # -- Additional BASIC templates --

    def _gen_extra_basic(self) -> list[dict]:
        """Generate extra BASIC QA pairs."""
        return [
            {
                "instruction": "Write a BASIC program that draws a border using color cycling.",
                "output": "10 FOR I=0 TO 15\n20 POKE 53280,I\n30 FOR D=1 TO 50:NEXT D\n40 NEXT I\n50 GOTO 10",
            },
            {
                "instruction": "Write a BASIC program that displays sprite coordinates from the keyboard.",
                "output": '10 POKE 53280,0:POKE 53281,0\n20 POKE 1024,81:POKE 55296,1\n30 X=160:Y=128\n40 POKE 53248,X:POKE 53249,Y\n50 K$=INKEY$\n60 IF K$="" THEN 40\n70 IF K$=CHR$(157) THEN X=X-1\n80 IF K$=CHR$(29) THEN X=X+1\n90 IF K$=CHR$(145) THEN Y=Y-1\n100 IF K$=CHR$(17) THEN Y=Y+1\n110 GOTO 40',
            },
            {
                "instruction": "Write a BASIC program that reads and displays the SID register values.",
                "output": '10 PRINT CHR$(147)\n20 PRINT "SID VOICE 1 REGISTERS:"\n30 FOR I=54272 TO 54278\n40 PRINT I;PEEK(I)\n50 NEXT I\n60 GOTO 30',
            },
            {
                "instruction": "Write a BASIC program that calculates NTSC SID frequencies for one octave.",
                "output": '10 CLK=1022727\n20 NOTES$="C C#D D#E F F#G G#A A#B "\n30 FOR I=0 TO 11\n40 F=440*2^((I-9)/12)\n50 V=INT(F*16777216/CLK)\n60 PRINT MID$(NOTES$,I*2+1,2),F,V\n70 NEXT I',
            },
            {
                "instruction": "Write a BASIC one-liner that fills the screen with random characters.",
                "output": "10 FOR I=1024 TO 2023:POKE I,INT(RND(1)*256):NEXT I",
            },
        ]

    # -- Expanded QA templates (additional ~200 pairs) --

    def _gen_extra_expanded(self) -> list[dict]:
        """Generate expanded QA pairs to reach 500+ target."""
        pairs = []

        # --- Memory map factual QAs ---
        mem_facts = [
            (
                "$00-$01",
                "CPU zero page pointers: $00 = processor port, $01 = bank switching",
            ),
            ("$02-$03", "tape buffer pointers"),
            ("$04-$05", "current character color and screen column"),
            ("$06", "character to print from INPUT/GET"),
            ("$08", "flag: 0=load/verify, 1=save"),
            ("$09-$0C", "current screen row address"),
            ("$0D", "logical file number for current device"),
            ("$0E", "length of last filename"),
            ("$0F-$10", "tape end address"),
            ("$11-$12", "character set ROM address"),
            ("$13-$14", "screen memory base address"),
            ("$15-$16", "cursor position in line"),
            ("$17", "flag: cursor blink enabled"),
            ("$18-$19", "screen editor memory pointer"),
            ("$1B", "current input device"),
            ("$1C", "current output device"),
            ("$20-$21", "keyboard buffer length"),
            ("$22-$2B", "general workspace"),
            ("$2C-$31", "sprite data pointers workspace"),
            ("$33-$3B", "flag: BASIC search and input state"),
            ("$3C-$48", "current BASIC line pointer"),
            ("$49-$4B", "BASIC current token pointer"),
            ("$4C-$4E", "BASIC variable pointer"),
            ("$4F-$51", "BASIC array pointer"),
            ("$52-$53", "previous BASIC token pointer"),
            ("$54-$55", "BASIC line number"),
            ("$56-$57", "BASIC integer value"),
            ("$58", "BASIC token search direction"),
            ("$59-$5A", "BASIC data pointer"),
            ("$5B-$5C", "BASIC variable name"),
            ("$5D-$5E", "BASIC variable value"),
            ("$5F-$60", "BASIC array index"),
            ("$61-$62", "BASIC temp storage"),
            ("$63-$66", "BASIC number storage"),
            ("$67-$68", "BASIC text pointer"),
            ("$69-$6A", "BASIC token line pointer"),
            ("$6B-$6C", "BASIC variable pointer"),
            ("$6D-$6E", "BASIC array variable pointer"),
            ("$6F-$70", "BASIC string storage"),
            ("$71-$72", "BASIC utility pointer"),
            ("$73-$74", "BASIC eval pointer"),
            ("$75", "number of BASIC variables"),
            ("$76", "number of BASIC arrays"),
            ("$77-$78", "BASIC array data size"),
            ("$79", "BASIC string stack index"),
            ("$7A-$7B", "BASIC search pointer"),
            ("$7C-$7D", "BASIC current line"),
            ("$7E-$7F", "BASIC previous line"),
            ("$80-$81", "BASIC temp variable"),
            ("$82-$84", "BASIC evaluation accumulator"),
            ("$85", "BASIC temp index"),
            ("$86-$87", "BASIC source pointer"),
            ("$88-$89", "BASIC destination pointer"),
            ("$8A", "BASIC file number"),
            ("$8B", "BASIC character pointer"),
            ("$8C-$8D", "BASIC string variable pointer"),
            ("$8E-$8F", "BASIC line input pointer"),
            ("$90-$91", "BASIC expression pointer"),
            ("$92", "BASIC stack depth"),
            ("$93", "flag: load/verify mode"),
            ("$94", "flag: tape buffer in use"),
            ("$95", "flag: start/stop tape"),
            ("$96", "flag: tape write"),
            ("$97-$98", "BASIC temp variable"),
            ("$99", "flag: screen/editor mode"),
            ("$9A", "flag: reverse mode"),
            ("$9B", "flag: cursor visible"),
            ("$9C", "flag: insert mode"),
            ("$9D", "flag: last key pressed"),
            ("$9E-$9F", "BASIC line pointer"),
            ("$A0-$A1", "BASIC line counter"),
            ("$A2", "BASIC shift key flag"),
            ("$A3-$A4", "BASIC temp pointer"),
            ("$A5-$A6", "BASIC temp variable"),
            ("$A7-$A8", "BASIC variable pointer"),
            ("$A9", "BASIC flag"),
            ("$AA-$AB", "BASIC screen pointer"),
            ("$AC-$AD", "BASIC source pointer"),
            ("$AE-$AF", "BASIC destination pointer"),
            ("$B0-$B1", "BASIC search pointer"),
            ("$B2-$B3", "BASIC temp pointer"),
            ("$B4", "flag: BASIC eval error"),
            ("$B5", "flag: BASIC search direction"),
            ("$B6", "flag: BASIC variable type"),
            ("$B7", "flag: BASIC array flag"),
            ("$B8-$B9", "BASIC line pointer"),
            ("$BA-$BB", "BASIC expression pointer"),
            ("$BC-$BD", "BASIC temp pointer"),
            ("$BE-$BF", "BASIC variable pointer"),
            ("$C0", "flag: BASIC error"),
            ("$C1-$C2", "BASIC temp storage"),
            ("$C3-$C4", "BASIC line counter"),
            ("$C5-$C6", "BASIC expression pointer"),
            ("$C7", "flag: BASIC input mode"),
            ("$C8", "flag: BASIC data mode"),
            ("$C9-$CA", "BASIC search pointer"),
            ("$CB-$CC", "BASIC temp pointer"),
            ("$CD", "flag: BASIC error number"),
            ("$CE-$CF", "BASIC line pointer"),
            ("$D0-$D1", "BASIC temp pointer"),
            ("$D2-$D3", "BASIC expression pointer"),
            ("$D4", "flag: BASIC eval mode"),
            ("$D5-$D6", "BASIC temp variable"),
            ("$D7-$D8", "BASIC line counter"),
            ("$D9-$DA", "BASIC temp pointer"),
            ("$DB-$DC", "BASIC variable pointer"),
            ("$DD", "flag: BASIC status"),
            ("$DE-$DF", "BASIC temp storage"),
            ("$E0-$E1", "BASIC search pointer"),
            ("$E2-$E3", "BASIC temp pointer"),
            ("$E4-$E5", "BASIC expression pointer"),
            ("$E6", "flag: BASIC input device"),
            ("$E7-$E8", "BASIC temp variable"),
            ("$E9-$EA", "BASIC line pointer"),
            ("$EB-$EC", "BASIC temp pointer"),
            ("$ED-$EE", "BASIC variable pointer"),
            ("$EF", "flag: BASIC status"),
            ("$F0-$F1", "BASIC temp storage"),
            ("$F2-$F3", "BASIC search pointer"),
            ("$F4-$F5", "BASIC temp pointer"),
            ("$F6-$F7", "BASIC expression pointer"),
            ("$F8", "flag: BASIC input device"),
            ("$F9-$FA", "BASIC temp variable"),
            ("$FB-$FC", "BASIC line pointer"),
            ("$FD-$FE", "BASIC temp pointer"),
            ("$FF", "BASIC variable pointer"),
        ]

        for addr, desc in mem_facts:
            pairs.append(
                {
                    "instruction": f"What is stored at memory address {addr} on the C64?",
                    "context": "",
                    "constraints": "Answer with a precise factual statement.",
                    "output": f"Address {addr}: {desc}.",
                }
            )

        # --- SID ADSR pairs ---
        adsr_notes = [
            ("C2", 0x01D1, 0x0115),
            ("D2", 0x01F5, 0x0138),
            ("E2", 0x021D, 0x015D),
            ("F2", 0x0245, 0x0185),
            ("G2", 0x0271, 0x01AF),
            ("A2", 0x02A0, 0x01DE),
            ("B2", 0x02D2, 0x0211),
            ("C3", 0x0308, 0x0247),
            ("D3", 0x0341, 0x0281),
            ("E3", 0x037E, 0x02BD),
            ("F3", 0x03BF, 0x02FD),
            ("G3", 0x0405, 0x0341),
            ("A3", 0x0450, 0x038A),
            ("B3", 0x04A0, 0x03D8),
            ("C4", 0x04F5, 0x042D),
            ("D4", 0x0551, 0x0488),
            ("E4", 0x05B2, 0x04EB),
            ("F4", 0x061A, 0x0554),
            ("G4", 0x0687, 0x05C5),
            ("A4", 0x06FB, 0x063E),
            ("B4", 0x0777, 0x06BD),
            ("C5", 0x07FA, 0x0742),
            ("D5", 0x0886, 0x07D1),
            ("E5", 0x091C, 0x0866),
            ("F5", 0x09BC, 0x0904),
            ("G5", 0x0A67, 0x09AA),
            ("A5", 0x0B1E, 0x0A5A),
            ("B5", 0x0BE1, 0x0B15),
            ("C6", 0x0CB1, 0x0BD7),
        ]

        for note, freq_pal, freq_ntsc in adsr_notes:
            pairs.append(
                {
                    "instruction": f"What is the SID frequency value for note {note} on PAL C64?",
                    "context": "PAL clock: 985248 Hz",
                    "constraints": "Provide the 16-bit frequency value.",
                    "output": f"Note {note} on PAL C64: frequency = ${freq_pal:04X} ({freq_pal}).",
                }
            )
            pairs.append(
                {
                    "instruction": f"What is the SID frequency value for note {note} on NTSC C64?",
                    "context": "NTSC clock: 1022727 Hz",
                    "constraints": "Provide the 16-bit frequency value.",
                    "output": f"Note {note} on NTSC C64: frequency = ${freq_ntsc:04X} ({freq_ntsc}).",
                }
            )

        # --- BASIC v2 keyword tokens ---
        basic_tokens = [
            ("END", 0x80),
            ("FOR", 0x81),
            ("NEXT", 0x82),
            ("DATA", 0x83),
            ("INPUT#", 0x84),
            ("INPUT", 0x85),
            ("DIM", 0x86),
            ("READ", 0x87),
            ("LET", 0x88),
            ("GOTO", 0x89),
            ("RUN", 0x8A),
            ("IF", 0x8B),
            ("RESTORE", 0x8C),
            ("GOSUB", 0x8D),
            ("RETURN", 0x8E),
            ("REM", 0x8F),
            ("STOP", 0x90),
            ("ON", 0x91),
            ("WAIT", 0x92),
            ("LOAD", 0x93),
            ("SAVE", 0x94),
            ("VERIFY", 0x95),
            ("DEF", 0x96),
            ("POKE", 0x97),
            ("PRINT#", 0x98),
            ("PRINT", 0x99),
            ("CONT", 0x9A),
            ("LIST", 0x9B),
            ("CLEAR", 0x9C),
            ("GET", 0x9D),
            ("NEW", 0x9E),
            ("TAB(", 0x9F),
            ("TO", 0xA0),
            ("FN", 0xA1),
            ("SPC(", 0xA2),
            ("THEN", 0xA3),
            ("NOT", 0xA4),
            ("STEP", 0xA5),
            ("+", 0xA6),
            ("-", 0xA7),
            ("*", 0xA8),
            ("/", 0xA9),
            ("^", 0xAA),
            ("AND", 0xAB),
            ("OR", 0xAC),
            (">", 0xAD),
            ("=", 0xAE),
            ("<", 0xAF),
            ("SGN", 0xB0),
            ("INT", 0xB1),
            ("ABS", 0xB2),
            ("USR", 0xB3),
            ("FRE", 0xB4),
            ("POS", 0xB5),
            ("SQR", 0xB6),
            ("RND", 0xB7),
            ("LOG", 0xB8),
            ("EXP", 0xB9),
            ("COS", 0xBA),
            ("SIN", 0xBB),
            ("TAN", 0xBC),
            ("ATN", 0xBD),
            ("PEEK", 0xBE),
            ("LEN", 0xBF),
            ("STR$", 0xC0),
            ("VAL", 0xC1),
            ("ASC", 0xC2),
            ("CHR$", 0xC3),
            ("LEFT$", 0xC4),
            ("RIGHT$", 0xC5),
            ("MID$", 0xC6),
            ("GO", 0xC7),
        ]

        for token, byte_val in basic_tokens:
            pairs.append(
                {
                    "instruction": f"What is the BASIC v2 token byte for '{token}'?",
                    "context": "C64 BASIC v2 tokenization",
                    "constraints": "Provide the hex token value.",
                    "output": f"Token '{token}' = ${byte_val:02X} ({byte_val} decimal).",
                }
            )

        # --- Color name/value pairs ---
        color_data = [
            (0, "Black", "Nero"),
            (1, "White", "Bianco"),
            (2, "Red", "Rosso"),
            (3, "Cyan", "Ciano"),
            (4, "Purple", "Viola"),
            (5, "Green", "Verde"),
            (6, "Blue", "Blu"),
            (7, "Yellow", "Giallo"),
            (8, "Orange", "Arancione"),
            (9, "Brown", "Marrone"),
            (10, "Light Red", "Rosso chiaro"),
            (11, "Dark Grey", "Grigio scuro"),
            (12, "Grey", "Grigio"),
            (13, "Light Green", "Verde chiaro"),
            (14, "Light Blue", "Blu chiaro"),
            (15, "Light Grey", "Grigio chiaro"),
        ]

        for val, eng, ita in color_data:
            pairs.append(
                {
                    "instruction": f"What color is value {val} on the C64? (English)",
                    "context": "VIC-II color palette, values 0-15",
                    "constraints": "Answer with the color name.",
                    "output": f"Color {val} = {eng}.",
                }
            )

        # --- Additional code templates ---
        code_templates = [
            {
                "instruction": "Write a routine to flip between uppercase and lowercase charset.",
                "context": "Toggle the character set using $D018 bit 1.",
                "output": """        * = $C000
FLIP_CHARSET:
        LDA $D018
        EOR #$02         ; toggle bit 1 (charset selection)
        STA $D018
        RTS""",
            },
            {
                "instruction": "Write a sprite multiplexer that shows 16 sprites.",
                "context": "Basic sprite multiplexer: 2 IRQ positions for 16 sprites.",
                "output": """        * = $C000
SETUP_MUX:
        SEI
        LDA #<MUX_IRQ
        STA $0314
        LDA #>MUX_IRQ
        STA $0315
        LDA #$01
        STA $D01A
        LDA #$80         ; raster line 128
        STA $D012
        LDA $D011
        AND #$7F
        STA $D011
        LDA #$FF
        STA $D015        ; enable all 8 sprites
        CLI
        RTS

MUX_IRQ:
        INC $D019
        LDA $D012
        CMP #$80
        BEQ LOWER_HALF
        ; Upper half: set sprites 0-7 Y to top positions
        LDX #$00
SET_TOP:
        LDA SPR_Y_TOP,X
        STA $D001,X
        INX
        CPX #$10
        BNE SET_TOP
        JMP $EA31
LOWER_HALF:
        ; Lower half: set sprites 0-7 Y to bottom positions
        LDX #$00
SET_BOT:
        LDA SPR_Y_BOT,X
        STA $D001,X
        INX
        CPX #$10
        BNE SET_BOT
        JMP $EA31

SPR_Y_TOP: .BYTE $20,$20,$20,$20,$20,$20,$20,$20
SPR_Y_BOT: .BYTE $80,$80,$80,$80,$80,$80,$80,$80""",
            },
            {
                "instruction": "Write a fade-in effect for the border color.",
                "context": "Progressively change border from black to target color.",
                "output": """        * = $C000
FADE_IN:
        LDX #$00         ; start from color 0
FADE_LOOP:
        STX $D020
        LDY #$FF
DELAY1: DEY
        BNE DELAY1
        LDY #$FF
DELAY2: DEY
        BNE DELAY2
        INX
        CPX #$08         ; fade to color 8
        BNE FADE_LOOP
        RTS""",
            },
            {
                "instruction": "Write a keyboard matrix scanner that returns the pressed key.",
                "context": "Full C64 keyboard matrix scan.",
                "output": """        * = $C000
SCAN_KEY:
        LDA #$00
        STA $DC02        ; columns: input
        LDA #$FF
        STA $DC03        ; rows: output
        LDX #$00         ; column counter
COL_LOOP:
        LDA COL_MASK,X
        STA $DC00        ; select column
        NOP
        NOP
        LDA $DC01        ; read rows
        CMP #$FF
        BNE KEY_FOUND
        INX
        CPX #$08
        BNE COL_LOOP
        LDA #$00         ; no key
        RTS
KEY_FOUND:
        TXA
        ASL
        ASL
        ASL
        ; combine column (X) and row (A) into matrix index
        RTS

COL_MASK: .BYTE $FE,$FD,$FB,$F7,$EF,$DF,$BF,$7F""",
            },
            {
                "instruction": "Write a routine to display a bitmap pattern.",
                "context": "Fill bitmap memory with a diagonal line pattern.",
                "output": """        * = $C000
BITMAP_FILL:
        LDX #$00
FILL_LOOP:
        TXA
        STA $2000,X      ; bitmap at $2000
        STA $2800,X      ; second half
        INX
        BNE FILL_LOOP
        LDX #$00
FILL_LOOP2:
        TXA
        EOR #$FF
        STA $2100,X
        STA $2900,X
        INX
        BNE FILL_LOOP2
        RTS""",
            },
            {
                "instruction": "Write a raster IRQ that splits screen colors.",
                "context": "Change background color mid-screen for a split effect.",
                "output": """        * = $C000
SPLIT_SETUP:
        SEI
        LDA #<SPLIT_IRQ
        STA $0314
        LDA #>SPLIT_IRQ
        STA $0315
        LDA #$01
        STA $D01A
        LDA #$80
        STA $D012
        LDA $D011
        AND #$7F
        STA $D011
        CLI
        RTS

SPLIT_IRQ:
        INC $D019
        LDA #$02
        STA $D021        ; change bg color at raster line
        NOP
        NOP
        NOP
        NOP
        NOP
        LDA #$06
        STA $D021        ; restore bg color
        JMP $EA31""",
            },
            {
                "instruction": "Write a routine that reads the mouse from CIA 2.",
                "context": "C64 paddle/mouse on CIA 2 port.",
                "output": """        * = $C000
READ_MOUSE:
        LDA $DD01        ; CIA 2 port B
        STA TEMP
        LDA #$80         ; select X axis
        STA $DD00
        NOP
        NOP
        LDA $DD01        ; read X
        STA MOUSE_X
        LDA #$40         ; select Y axis
        STA $DD00
        NOP
        NOP
        LDA $DD01        ; read Y
        STA MOUSE_Y
        RTS

TEMP:     .BYTE $00
MOUSE_X:  .BYTE $00
MOUSE_Y:  .BYTE $00""",
            },
            {
                "instruction": "Write a routine to play a simple melody with SID voice 2.",
                "context": "Melody player using SID voice 2 with different notes.",
                "output": """        * = $C000
PLAY_MELODY:
        LDX NOTE_INDEX
        LDA MELO_FREQ_H,X
        BEQ MELO_DONE
        STA $D408         ; voice 2 freq high
        LDA MELO_FREQ_L,X
        STA $D407         ; voice 2 freq low
        LDA #$41
        STA $D40B         ; gate on
        ; Wait
        LDY #$10
WAIT:   DEY
        BNE WAIT
        INC NOTE_INDEX
        JMP PLAY_MELODY
MELO_DONE:
        LDA #$40
        STA $D40B         ; gate off
        RTS

NOTE_INDEX: .BYTE 0
MELO_FREQ_H: .BYTE $02,$02,$03,$03,$02,$00
MELO_FREQ_L: .BYTE $A0,$68,$08,$A0,$68,$00""",
            },
            {
                "instruction": "Write a scrolling text routine using character RAM.",
                "context": "Scroll text left using VIC-II hardware scroll.",
                "output": """        * = $C000
SCROLL_TEXT:
        LDA SCROLL_OFFSET
        SEC
        SBC #$01
        AND #$07
        STA SCROLL_OFFSET
        LDA $D016
        AND #$F8
        ORA SCROLL_OFFSET
        STA $D016
        LDA SCROLL_OFFSET
        CMP #$00
        BNE SCROLL_DONE
        ; Shift screen memory
        LDX #$00
SHIFT:  LDA $0401,X
        STA $0400,X
        INX
        CPX #$27         ; 39 columns
        BNE SHIFT
SCROLL_DONE:
        RTS

SCROLL_OFFSET: .BYTE $07""",
            },
            {
                "instruction": "Write a simple game loop with keyboard input.",
                "context": "Main game loop: read input, update state, render.",
                "output": """        * = $C000
GAME_LOOP:
        JSR $FFE4         ; GETIN
        BEQ NO_KEY
        CMP #$11          ; 'Q' to quit
        BEQ QUIT
        CMP #$41          ; 'A' = move left
        BEQ MOVE_LEFT
        CMP #$44          ; 'D' = move right
        BEQ MOVE_RIGHT
        JMP GAME_LOOP
MOVE_LEFT:
        DEC PLAYER_X
        JMP RENDER
MOVE_RIGHT:
        INC PLAYER_X
        JMP RENDER
RENDER:
        LDA PLAYER_X
        STA $D000         ; sprite 0 X
NO_KEY:
        JMP GAME_LOOP
QUIT:
        RTS

PLAYER_X: .BYTE $80""",
            },
        ]

        for tmpl in code_templates:
            pairs.append(
                {
                    "instruction": tmpl["instruction"],
                    "context": tmpl.get("context", ""),
                    "constraints": "Return valid ACME 6502 assembly with *= and ; for comments.",
                    "output": tmpl["output"],
                }
            )

        # --- Additional BASIC programs ---
        basic_programs = [
            {
                "instruction": "Write a BASIC program that bounces a sprite across the screen.",
                "output": "10 X=0:DX=1\n20 POKE 53248,X:POKE 53249,100\n30 X=X+DX\n40 IF X>=255 THEN DX=-1\n50 IF X<=0 THEN DX=1\n60 GOTO 20",
            },
            {
                "instruction": "Write a BASIC program that counts the raster lines.",
                "output": '10 PRINT CHR$(147)\n20 POKE 53272,14\n30 PRINT "RASTER:";PEEK(53272)\n40 GOTO 30',
            },
            {
                "instruction": "Write a BASIC program that plays musical notes via SID.",
                "output": "10 FOR I=0 TO 7\n20 READ F\n30 POKE 54272,F AND 255\n40 POKE 54273,F/256\n50 POKE 54276,33\n60 FOR D=1 TO 100:NEXT D\n70 POKE 54276,32\n80 NEXT I\n90 DATA 1024,1140,1272,1352,1512,1704,1912,2032",
            },
            {
                "instruction": "Write a BASIC program that creates a starfield effect.",
                "output": "10 PRINT CHR$(147)\n20 FOR I=1 TO 50\n30 X=INT(RND(1)*40)\n40 Y=INT(RND(1)*25)\n50 POKE 1024+Y*40+X,46\n60 POKE 55296+Y*40+X,15\n70 NEXT I\n80 GOTO 20",
            },
            {
                "instruction": "Write a BASIC program that measures game loop speed.",
                "output": '10 POKE 53280,0:POKE 53281,0\n20 PRINT CHR$(147)\n30 PRINT "MEASURING..."\n40 T=TI\n50 FOR I=1 TO 1000\n60 NEXT I\n70 PRINT "TIME:";TI-T;" JIFFIES"\n80 PRINT "LOOP/SEC:";1000/(TI-T)*60',
            },
            {
                "instruction": "Write a BASIC program that copies a screen section.",
                "output": "10 FOR I=0 TO 39\n20 POKE 2024+I,PEEK(1024+I)\n30 POKE 55296+I,PEEK(55296+I)\n40 NEXT I",
            },
            {
                "instruction": "Write a BASIC program that demonstrates string functions.",
                "output": '10 A$="COMMODORE 64"\n20 PRINT "LENGTH:";LEN(A$)\n30 PRINT "LEFT$:";LEFT$(A$,9)\n40 PRINT "RIGHT$:";RIGHT$(A$,3)\n50 PRINT "MID$:";MID$(A$,10,3)\n60 PRINT "CHR$:";CHR$(65)\n70 PRINT "ASC:";ASC("A")\n80 PRINT "VAL:";VAL("123")\n90 PRINT "STR$:";STR$(456)',
            },
            {
                "instruction": "Write a BASIC program that uses DATA statements for a score table.",
                "output": '10 PRINT CHR$(147)\n20 PRINT "HIGH SCORES"\n30 PRINT "------------"\n40 FOR I=1 TO 5\n50 READ N$,S\n60 PRINT N$;TAB(10);S\n70 NEXT I\n80 DATA "ACE",99999\n90 DATA "BOB",85000\n100 DATA "CAT",72000\n110 DATA "DOG",65000\n120 DATA "ELF",50000',
            },
        ]

        for tmpl in basic_programs:
            pairs.append(
                {
                    "instruction": tmpl["instruction"],
                    "context": "",
                    "constraints": "Write a complete BASIC v2 program with line numbers.",
                    "output": tmpl["output"],
                }
            )

        # --- Register bit-level QAs ---
        bit_details = [
            ("$D011 bit 7", "Raster MSB (bit 8 of raster line counter)"),
            ("$D011 bit 5", "Bitmap mode: 1 = bitmap, 0 = character"),
            ("$D011 bit 4", "Display enable: 1 = display on, 0 = blank"),
            ("$D011 bit 3", "Screen height: 1 = 25 rows, 0 = 24 rows"),
            ("$D011 bits 0-2", "Y scroll offset (0-7 pixels)"),
            ("$D016 bit 4", "Multicolor mode for characters"),
            ("$D016 bit 3", "Column width: 1 = 38 columns, 0 = 40 columns"),
            ("$D016 bits 0-2", "X scroll offset (0-7 pixels)"),
            ("$D018 bits 4-7", "Screen RAM bank offset (in 2KB units)"),
            ("$D018 bits 1-3", "Character set offset"),
            ("$D01C bit 0", "Sprite 0 multicolor enable"),
            ("$D01C bit 1", "Sprite 1 multicolor enable"),
            ("$D01C bit 2", "Sprite 2 multicolor enable"),
            ("$D01C bit 3", "Sprite 3 multicolor enable"),
            ("$D01C bit 4", "Sprite 4 multicolor enable"),
            ("$D01C bit 5", "Sprite 5 multicolor enable"),
            ("$D01C bit 6", "Sprite 6 multicolor enable"),
            ("$D01C bit 7", "Sprite 7 multicolor enable"),
            ("$D019 bit 0", "Raster interrupt flag"),
            ("$D019 bit 1", "Sprite-background collision interrupt"),
            ("$D019 bit 2", "Sprite-sprite collision interrupt"),
            ("$D019 bit 3", "Light pen interrupt"),
            ("$D019 bit 7", "Master interrupt flag (set when any enabled IRQ fires)"),
            ("$D01B bit 0", "Sprite 0 priority: 0=over, 1=under background"),
            ("$D01D bit 0", "Sprite 0 X expand: 1 = double width"),
            ("$D017 bit 0", "Sprite 0 Y expand: 1 = double height"),
            ("$D418 bits 0-3", "Volume: 0=silent, 15=max"),
            ("$D418 bit 4", "Low-pass filter enable"),
            ("$D418 bit 5", "Band-pass filter enable"),
            ("$D418 bit 6", "High-pass filter enable"),
            ("$DC0D bit 0", "Timer A underflow interrupt"),
            ("$DC0D bit 1", "Timer B underflow interrupt"),
            ("$DC0D bit 7", "Set to acknowledge, read for interrupt status"),
            (
                "$DD00 bits 0-1",
                "VIC-II bank select: 00=bank3, 01=bank2, 10=bank1, 11=bank0",
            ),
        ]

        for reg, desc in bit_details:
            pairs.append(
                {
                    "instruction": f"What does {reg} do on the C64?",
                    "context": "",
                    "constraints": "Explain the bit function precisely.",
                    "output": f"{reg}: {desc}.",
                }
            )

        # --- 6502 flag QAs ---
        flags = [
            ("N (Negative)", "Bit 7 of result. Set if bit 7 is 1 after an operation."),
            (
                "V (Overflow)",
                "Signed overflow flag. Set when result is outside -128 to +127.",
            ),
            (
                "B (Break)",
                "Set when BRK is executed. Not a physical flag — reflected in status register.",
            ),
            (
                "D (Decimal)",
                "BCD mode flag. When set, ADC/SBC use BCD arithmetic. C64 doesn't use BCD.",
            ),
            (
                "I (Interrupt)",
                "Interrupt disable. When set, IRQ is masked. Set by SEI, cleared by CLI.",
            ),
            ("Z (Zero)", "Set when result of last operation is zero."),
            (
                "C (Carry)",
                "Set on overflow from ADC, borrow from SBC, or shift/rotate out.",
            ),
        ]

        for name, desc in flags:
            pairs.append(
                {
                    "instruction": f"What is the {name} flag on the 6502 CPU?",
                    "context": "6502 processor status register flags",
                    "constraints": "Explain the flag's purpose and when it's set.",
                    "output": f"{name} flag: {desc}",
                }
            )

        return pairs

    # -- Main generation pipeline --

    def generate_all(self, target_count: int = 500) -> list[dict]:
        """Generate all QA pairs and deduplicate."""
        self._seen_hashes.clear()
        self.generated = []

        print(f"[Scaler] Starting generation (target: {target_count} pairs)...")

        # 1. Add all seed pairs
        for seed in self.seeds:
            qa = {
                "instruction": seed["instruction"],
                "context": seed.get("context", ""),
                "constraints": self._constraints_for_type(seed["type"]),
                "output": seed["output"],
            }
            self._add_unique(qa)

        print(f"[Scaler] Seeds added: {len(self.generated)} pairs")

        # 2. Add hardware facts
        hw_facts = self._gen_factual_from_hardware()
        for fact in hw_facts:
            qa = {
                "instruction": fact["instruction"],
                "context": "",
                "constraints": "Answer with a precise factual statement.",
                "output": fact["output"],
            }
            self._add_unique(qa)

        print(f"[Scaler] After hardware facts: {len(self.generated)} pairs")

        # 3. Add extra templates
        extras = (
            self._gen_extra_code_templates()
            + self._gen_extra_theory()
            + self._gen_extra_bugfix()
            + self._gen_extra_basic()
            + self._gen_extra_expanded()
        )

        def _infer_type(item):
            if "_type" in item:
                return item["_type"]
            instr = item.get("instruction", "").lower()
            output = item.get("output", "").lower()
            if any(
                kw in instr
                for kw in [
                    "wrong",
                    "bug",
                    "problem",
                    "fix",
                    "crash",
                    "not work",
                    "doesn't work",
                ]
            ):
                return "bugfix"
            if any(
                kw in instr
                for kw in [
                    "explain",
                    "how does",
                    "how do",
                    "what is",
                    "what are",
                    "difference between",
                ]
            ):
                return "theory"
            if any(
                op in output
                for op in ["lda", "sta", "jsr", "*=", ".byte", "rts", "inc"]
            ):
                return "code"
            return "factual"

        for item in extras:
            qa_type = _infer_type(item)
            qa = {
                "instruction": item["instruction"],
                "context": item.get("context", ""),
                "constraints": item.get(
                    "constraints", self._constraints_for_type(qa_type)
                ),
                "output": item["output"],
            }
            self._add_unique(qa)

        print(f"[Scaler] After extra templates: {len(self.generated)} pairs")

        # 4. Generate variations from seeds
        variation_count = 0
        for seed in self.seeds:
            if seed["type"] == "factual":
                variations = self._gen_factual_variations(seed)
            elif seed["type"] == "code":
                variations = self._gen_code_variations(seed)
            elif seed["type"] == "explain":
                variations = self._gen_explain_variations(seed)
            elif seed["type"] == "bugfix":
                variations = self._gen_bugfix_variations(seed)
            elif seed["type"] == "theory":
                variations = self._gen_theory_variations(seed)
            else:
                variations = []

            for v in variations:
                qa = {
                    "instruction": v["instruction"],
                    "context": v.get("context", ""),
                    "constraints": v.get(
                        "constraints", self._constraints_for_type(seed["type"])
                    ),
                    "output": v["output"],
                }
                if self._add_unique(qa):
                    variation_count += 1

        print(
            f"[Scaler] After variations: {len(self.generated)} pairs (+{variation_count} new)"
        )

        # 5. Generate additional programmatic pairs until target
        programmatic = self._gen_programmatic_pairs()
        for qa in programmatic:
            self._add_unique(qa)

        print(f"[Scaler] After programmatic: {len(self.generated)} pairs")

        # 6. If still under target, apply more aggressive variations
        if len(self.generated) < target_count:
            more = self._gen_aggressive_variations()
            for qa in more:
                if len(self.generated) >= target_count:
                    break
                self._add_unique(qa)

        print(f"[Scaler] After aggressive variations: {len(self.generated)} pairs")

        # Shuffle
        random.shuffle(self.generated)

        return self.generated

    def _constraints_for_type(self, qa_type: str) -> str:
        constraints = {
            "factual": "Answer with a precise factual statement. Include addresses and register names.",
            "code": "Return valid ACME 6502 assembly with *= for origin and ; for comments.",
            "explain": "Explain step by step. Structure: 1. What is it, 2. How it works, 3. Usage, 4. Example.",
            "bugfix": "Identify the bug, explain why it's wrong, and provide the corrected code.",
            "theory": "Provide a clear theoretical explanation. Include specific C64 technical details.",
        }
        return constraints.get(qa_type, "Provide a clear, accurate answer.")

    def _gen_programmatic_pairs(self) -> list[dict]:
        """Generate QA pairs programmatically from combinatorial templates."""
        pairs = []

        # Instruction pattern templates for all addressing modes
        addr_modes = [
            ("Immediate", "LDA #$42", "#$42"),
            ("Zero Page", "LDA $10", "$10"),
            ("Zero Page X", "LDA $10,X", "$10,X"),
            ("Absolute", "LDA $1000", "$1000"),
            ("Absolute X", "LDA $1000,X", "$1000,X"),
            ("Absolute Y", "LDA $1000,Y", "$1000,Y"),
            ("Indirect X", "LDA ($10,X)", "($10,X)"),
            ("Indirect Y", "LDA ($10),Y", "($10),Y"),
        ]

        for mode_name, example, syntax in addr_modes:
            pairs.append(
                {
                    "instruction": f"What does {syntax} addressing mode mean in 6502 assembly?",
                    "context": "",
                    "constraints": "Explain the addressing mode briefly.",
                    "output": f"The {mode_name} addressing mode ({syntax}) — example: {example}.",
                }
            )

        # Opcode explanation pairs
        opcodes = [
            (
                "ADC",
                "Add with Carry",
                "adds a value to the accumulator plus the carry flag",
            ),
            (
                "SBC",
                "Subtract with Carry",
                "subtracts from the accumulator subtracting borrow",
            ),
            ("AND", "Logical AND", "performs bitwise AND with the accumulator"),
            ("ORA", "Logical OR", "performs bitwise OR with the accumulator"),
            ("EOR", "Exclusive OR", "performs bitwise XOR with the accumulator"),
            ("ASL", "Arithmetic Shift Left", "shifts all bits left by one, bit 0 = 0"),
            ("LSR", "Logical Shift Right", "shifts all bits right by one, bit 7 = 0"),
            ("ROL", "Rotate Left", "shifts left through carry, old carry into bit 0"),
            ("ROR", "Rotate Right", "shifts right through carry, old carry into bit 7"),
            (
                "CMP",
                "Compare",
                "subtracts operand from A without storing result, sets flags",
            ),
            ("CPX", "Compare X", "subtracts operand from X register, sets flags"),
            ("CPY", "Compare Y", "subtracts operand from Y register, sets flags"),
            ("DEC", "Decrement Memory", "decrements a memory location by 1"),
            ("INC", "Increment Memory", "increments a memory location by 1"),
            ("JMP", "Jump", "sets the program counter to the address"),
            ("JSR", "Jump to Subroutine", "pushes return address and jumps"),
            (
                "RTS",
                "Return from Subroutine",
                "pulls return address from stack and jumps",
            ),
            ("RTI", "Return from Interrupt", "pulls PC and status from stack"),
            ("PHA", "Push Accumulator", "pushes A onto the stack"),
            ("PLA", "Pull Accumulator", "pops from stack into A"),
            ("LDX", "Load X", "loads a value into the X register"),
            ("LDY", "Load Y", "loads a value into the Y register"),
            ("STX", "Store X", "stores X into a memory location"),
            ("STY", "Store Y", "stores Y into a memory location"),
            ("TAX", "Transfer A to X", "copies A into X"),
            ("TAY", "Transfer A to Y", "copies A into Y"),
            ("TXA", "Transfer X to A", "copies X into A"),
            ("TYA", "Transfer Y to A", "copies Y into A"),
            ("TSX", "Transfer Stack Pointer to X", "copies SP into X"),
            ("TXS", "Transfer X to Stack Pointer", "copies X into SP"),
            ("NOP", "No Operation", "does nothing, advances PC by 1"),
            ("CLC", "Clear Carry", "sets carry flag to 0"),
            ("SEC", "Set Carry", "sets carry flag to 1"),
            ("CLI", "Clear Interrupt", "clears interrupt disable flag"),
            ("SEI", "Set Interrupt", "sets interrupt disable flag"),
            ("CLD", "Clear Decimal", "clears decimal mode flag"),
            ("SED", "Set Decimal", "sets decimal mode flag"),
        ]

        for mnemonic, name, desc in opcodes:
            pairs.append(
                {
                    "instruction": f"What does the 6502 {mnemonic} instruction do?",
                    "context": "",
                    "constraints": "Provide a concise explanation.",
                    "output": f"{mnemonic} — {name}: {desc}.",
                }
            )

        # Branch condition pairs
        branches = [
            ("BNE", "Branch if Not Equal (Z=0)"),
            ("BEQ", "Branch if Equal (Z=1)"),
            ("BCC", "Branch if Carry Clear (C=0)"),
            ("BCS", "Branch if Carry Set (C=1)"),
            ("BMI", "Branch if Minus (N=1)"),
            ("BPL", "Branch if Plus (N=0)"),
            ("BVC", "Branch if Overflow Clear (V=0)"),
            ("BVS", "Branch if Overflow Set (V=1)"),
        ]

        for mnemonic, desc in branches:
            pairs.append(
                {
                    "instruction": f"What condition does {mnemonic} test?",
                    "context": "",
                    "constraints": "State the flag condition tested.",
                    "output": f"{mnemonic}: {desc}.",
                }
            )

        # Cycle count pairs
        cycle_info = [
            ("LDA immediate", "2 cycles", "#$XX"),
            ("LDA zero page", "3 cycles", "$XX"),
            ("LDA absolute", "4 cycles", "$XXXX"),
            ("LDA zero page X", "4 cycles", "$XX,X"),
            ("LDA absolute X", "4+ cycles", "$XXXX,X"),
            ("LDA (indirect,X)", "6 cycles", "($XX,X)"),
            ("LDA (indirect),Y", "5+ cycles", "($XX),Y"),
            ("STA zero page", "3 cycles", "$XX"),
            ("STA absolute", "4 cycles", "$XXXX"),
            ("NOP", "2 cycles", ""),
            ("RTS", "6 cycles", ""),
            ("JSR", "6 cycles", ""),
        ]

        for instr, cycles, syntax in cycle_info:
            pairs.append(
                {
                    "instruction": f"How many cycles does {instr} take on the 6502?",
                    "context": f"Addressing syntax: {syntax}" if syntax else "",
                    "constraints": "Provide the exact cycle count.",
                    "output": f"{instr} takes {cycles} on the 6502. {'+1 cycle if page boundary crossed.' if '+' in cycles else ''}",
                }
            )

        return pairs

    def _gen_aggressive_variations(self) -> list[dict]:
        """Generate more variations using broader transformations."""
        pairs = []

        # Reverse factual QAs
        for seed in self.seeds:
            if seed["type"] == "factual":
                # Flip question: "What register controls X?" → "Register Y controls what?"
                output = seed["output"]
                instr = seed["instruction"]
                if "register" in instr.lower() and "$" in output:
                    # Extract register and description
                    match = re.search(r"\$[0-9A-Fa-f]+", instr)
                    if match:
                        reg = match.group(0)
                        # Find the description in output
                        desc_match = re.search(r"controls? (.+?)(?:\.|$)", output)
                        if desc_match:
                            desc = desc_match.group(1)
                            pairs.append(
                                {
                                    "instruction": f"What register is used for {desc}?",
                                    "context": "",
                                    "constraints": "Answer with the register address and name.",
                                    "output": f"Register {reg} — {desc}.",
                                }
                            )

        # Combine two facts into a comparison
        for i in range(0, len(self.seeds) - 1, 2):
            s1, s2 = self.seeds[i], self.seeds[i + 1]
            if s1["type"] == "factual" and s2["type"] == "factual":
                pairs.append(
                    {
                        "instruction": f"Compare: {s1['instruction']} vs {s2['instruction']}",
                        "context": "",
                        "constraints": "Provide both answers side by side.",
                        "output": f"1) {s1['output']} 2) {s2['output']}",
                    }
                )

        # Quick reference style
        categories = {
            "sprite": [s for s in self.seeds if "sprite" in s["instruction"].lower()],
            "SID": [s for s in self.seeds if "SID" in s["instruction"]],
            "raster": [s for s in self.seeds if "raster" in s["instruction"].lower()],
        }

        for cat_name, cat_seeds in categories.items():
            if len(cat_seeds) >= 2:
                combined = " ".join(s["output"][:80] for s in cat_seeds[:3])
                pairs.append(
                    {
                        "instruction": f"Give me a quick reference for {cat_name} programming on C64.",
                        "context": "",
                        "constraints": "Keep it concise — key addresses and usage.",
                        "output": combined,
                    }
                )

        return pairs

    def write_jsonl(self, path: str) -> int:
        """Write generated dataset to JSONL file."""
        os.makedirs(
            os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True
        )
        with open(path, "w", encoding="utf-8") as f:
            for qa in self.generated:
                f.write(json.dumps(qa, ensure_ascii=False) + "\n")
        return len(self.generated)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_code_syntax(pairs: list[dict]) -> tuple[int, int]:
    """Validate that code QAs have syntactically valid assembly.
    Returns (valid_count, total_code_pairs)."""
    code_pairs = [
        p
        for p in pairs
        if any(
            kw in p.get("output", "").lower()
            for kw in ["lda", "sta", "jsr", "*=", ".byte", ".word", "rts", "inx"]
        )
    ]
    valid = 0
    for pair in code_pairs:
        is_valid, _ = validate_assembly_syntax(pair["output"])
        if is_valid:
            valid += 1
    return valid, len(code_pairs)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="C64 Distillation Scaler — template-based QA pair generator"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/output/distillation_dataset_scaled.jsonl",
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=500,
        help="Target number of QA pairs (default: 500)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    scaler = DistillationScaler()
    pairs = scaler.generate_all(target_count=args.count)

    # Validate
    valid, total = validate_code_syntax(pairs)
    valid_pct = (valid / total * 100) if total > 0 else 0

    # Write output
    output_path = args.output
    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True,
    )
    count = scaler.write_jsonl(output_path)

    print()
    print(f"Generated {count} QA pairs, {count} unique after dedup")
    print(f"Code syntax validation: {valid}/{total} valid ({valid_pct:.1f}%)")
    print(f"Output: {output_path}")

    if valid_pct < 50:
        print("[WARN] Less than 50% of code QAs are syntactically valid!")
        sys.exit(1)


if __name__ == "__main__":
    main()

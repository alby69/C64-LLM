---
title: "C64 Quick Reference Card"
description: "Scheda di riferimento rapido per la programmazione Commodore 64"
tags: [c64, quick-reference, cheat-sheet, memory-map, registers]
source: "Commodore 64 Programmer's Reference Guide, Quick Reference Card"
---

# Quick Reference Card - Commodore 64

## Registri principali

### VIC-II (Video) - Base $D000 (53248)

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| SP0X-SP7X | 53248-53262 | Sprite X coordinates |
| SP0Y-SP7Y | 53249-53263 | Sprite Y coordinates |
| MSIGX | 53264 | Sprite X MSB |
| SCROLY | 53265 | Control register 1 |
| RASTER | 53266 | Raster line |
| SPENA | 53269 | Sprite enable |
| SCROLX | 53270 | Control register 2 |
| YXPAND | 53271 | Sprite Y expand |
| VMCSB | 53272 | Memory pointers |
| VICIRQ | 53273 | Interrupt register |
| IRQMASK | 53274 | Interrupt enable |
| SPBGPR | 53275 | Sprite priority |
| SPMC | 53276 | Sprite multicolor |
| XXPAND | 53277 | Sprite X expand |
| SPSPCL | 53278 | Sprite-sprite collision |
| SPBGCL | 53279 | Sprite-background collision |
| EXTCOL | 53280 | Border color |
| BGCOL0 | 53281 | Background color 0 |
| BGCOL1 | 53282 | Background color 1 |
| BGCOL2 | 53283 | Background color 2 |
| BGCOL3 | 53284 | Background color 3 |
| SPMC0 | 53285 | Sprite multicolor 0 |
| SPMC1 | 53286 | Sprite multicolor 1 |
| SP0COL-SP7COL | 53287-53294 | Sprite colors |

### SID (Audio) - Base $D400 (54272)

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| FRELO1/FREHI1 | 54272-54273 | Voice 1 frequency |
| PWLO1/PWHI1 | 54274-54275 | Voice 1 pulse width |
| VCREG1 | 54276 | Voice 1 control |
| ATDCY1 | 54277 | Voice 1 attack/decay |
| SUREL1 | 54278 | Voice 1 sustain/release |
| FRELO2/FREHI2 | 54279-54280 | Voice 2 frequency |
| PWLO2/PWHI2 | 54281-54282 | Voice 2 pulse width |
| VCREG2 | 54283 | Voice 2 control |
| ATDCY2 | 54284 | Voice 2 attack/decay |
| SUREL2 | 54285 | Voice 2 sustain/release |
| FRELO3/FREHI3 | 54286-54287 | Voice 3 frequency |
| PWLO3/PWHI3 | 54288-54289 | Voice 3 pulse width |
| VCREG3 | 54290 | Voice 3 control |
| ATDCY3 | 54291 | Voice 3 attack/decay |
| SUREL3 | 54292 | Voice 3 sustain/release |
| CUTLO/CUTHI | 54293-54294 | Filter cutoff |
| RESON | 54295 | Filter resonance/voice |
| SIGVOL | 54296 | Volume/filter mode |

### CIA #1 - Base $DC00 (56320)

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| PRA | 56320 | Port A (keyboard, joystick 2) |
| PRB | 56321 | Port B (keyboard, joystick 1) |
| DDRA | 56322 | Data direction A |
| DDRB | 56323 | Data direction B |
| TA LO/HI | 56324-56325 | Timer A |
| TB LO/HI | 56326-56327 | Timer B |
| TOD | 56328-56331 | Time of day clock |
| ICR | 56333 | Interrupt control |
| CRA/CRB | 56334-56335 | Control registers |

### CIA #2 - Base $DD00 (56576)

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| PRA | 56576 | Port A (serial bus, VIC bank) |
| PRB | 56577 | Port B (RS-232, user port) |
| DDRA | 56578 | Data direction A |
| DDRB | 56579 | Data direction B |

## Colori

| Codice | Nome | Codice | Nome |
|--------|------|--------|------|
| 0 | Nero | 8 | Arancione |
| 1 | Bianco | 9 | Marrone |
| 2 | Rosso | 10 | Rosa chiaro |
| 3 | Ciano | 11 | Grigio scuro |
| 4 | Viola | 12 | Grigio medio |
| 5 | Verde | 13 | Verde chiaro |
| 6 | Blu | 14 | Azzurro chiaro |
| 7 | Giallo | 15 | Grigio chiaro |

## Mappa memoria essenziale

```
$0000-$00FF  Zero Page
$0100-$01FF  Stack
$0200-$02FF  Buffer input
$0300-$03FF  Area dati BASIC/KERNAL
$0400-$07FF  Screen Memory
$0800-$9FFF  BASIC RAM
$A000-$BFFF  BASIC ROM
$C000-$CFFF  RAM libera
$D000-$DFFF  I/O / Color RAM / VIC / SID / CIA
$E000-$FFFF  KERNAL ROM
```

## KERNAL Jump Table

| Routine | Indirizzo |
|---------|-----------|
| CINT | $FF81 |
| IOINIT | $FF84 |
| RAMTAS | $FF87 |
| RESTOR | $FF8A |
| VECTOR | $FF8D |
| SETMSG | $FF90 |
| SECOND | $FF93 |
| TKSA | $FF96 |
| MEMTOP | $FF99 |
| MEMBOT | $FF9C |
| SCNKEY | $FF9F |
| ACPTR | $FFA5 |
| CIOUT | $FFA8 |
| UNTLK | $FFAB |
| UNLSN | $FFAE |
| LISTEN | $FFB1 |
| TALK | $FFB4 |
| READST | $FFB7 |
| SETLFS | $FFBA |
| SETNAM | $FFBD |
| OPEN | $FFC0 |
| CLOSE | $FFC3 |
| CHKIN | $FFC6 |
| CHKOUT | $FFC9 |
| CLRCHN | $FFCC |
| CHRIN | $FFCF |
| CHROUT | $FFD2 |
| LOAD | $FFD5 |
| SAVE | $FFD8 |
| STOP | $FFE1 |
| GETIN | $FFE4 |
| CLALL | $FFE7 |
| SCREEN | $FFED |
| PLOT | $FFF0 |
| IOBASE | $FFF3 |

## Device numbers

| Device | Numero |
|--------|--------|
| Cassette | 1 |
| RS-232 | 2 |
| Screen | 3 |
| Printer | 4-5 |
| Floppy disk | 8-11 |

## Istruzioni 6502 comuni

| Istruzione | Descrizione |
|------------|-------------|
| LDA | Load Accumulator |
| LDX | Load X register |
| LDY | Load Y register |
| STA | Store Accumulator |
| STX | Store X register |
| STY | Store Y register |
| ADC | Add with Carry |
| SBC | Subtract with Carry |
| INC | Increment memory |
| DEC | Decrement memory |
| INX | Increment X |
| INY | Increment Y |
| DEX | Decrement X |
| DEY | Decrement Y |
| AND | Logical AND |
| ORA | Logical OR |
| EOR | Exclusive OR |
| ASL | Arithmetic Shift Left |
| LSR | Logical Shift Right |
| ROL | Rotate Left |
| ROR | Rotate Right |
| CMP | Compare with A |
| CPX | Compare with X |
| CPY | Compare with Y |
| BCC | Branch if Carry Clear |
| BCS | Branch if Carry Set |
| BEQ | Branch if Equal |
| BNE | Branch if Not Equal |
| BMI | Branch if Minus |
| BPL | Branch if Plus |
| JMP | Jump |
| JSR | Jump to Subroutine |
| RTS | Return from Subroutine |
| RTI | Return from Interrupt |
| PHA | Push A |
| PLA | Pull A |
| PHP | Push P |
| PLP | Pull P |
| TAX | Transfer A to X |
| TXA | Transfer X to A |
| TAY | Transfer A to Y |
| TYA | Transfer Y to A |
| TSX | Transfer SP to X |
| TXS | Transfer X to SP |
| BRK | Break |
| NOP | No Operation |
| CLC | Clear Carry |
| SEC | Set Carry |
| CLI | Clear Interrupt |
| SEI | Set Interrupt |
| CLV | Clear Overflow |
| CLD | Clear Decimal |
| SED | Set Decimal |

---

*Scheda di riferimento rapido - Commodore 64 Programmer's Reference Guide*

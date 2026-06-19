---
title: "BASIC to Machine Language"
description: "Guida completa alla programmazione in linguaggio macchina 6502 per Commodore 64"
tags: [c64, machine-language, assembly, 6502, memory, kernal]
source: "Commodore 64 Programmer's Reference Guide, Chapter 5"
---

# Capitolo 5: BASIC to Machine Language

## Cos'è il Machine Language?

Il linguaggio macchina è il linguaggio nativo del microprocessore **MOS 6510** del Commodore 64. A differenza del BASIC, che è interpretato, il linguaggio macchina viene eseguito direttamente dal processore.

### Vantaggi del Machine Language
- Velocità molto superiore al BASIC
- Controllo diretto dell'hardware
- Accesso a tutte le funzionalità del sistema
- Memoria utilizzata in modo efficiente

### Come appare il codice macchina
- Istruzioni rappresentate da numeri (byte)
- Ogni istruzione ha un codice operativo (opcode)
- Può includere operandi (dati/indirizze)

## Mappa memoria semplificata del Commodore 64

```
$0000-$00FF  (0-255)     : Zero Page - Area dati veloce
$0100-$01FF  (256-511)   : Stack
$0200-$02FF  (512-767)   : Buffer input tastiera
$0300-$03FF  (768-1023)  : Area dati BASIC/KERNAL
$0400-$07FF  (1024-2047) : Screen Memory (40x25)
$0800-$9FFF  (2048-40959): BASIC RAM libera
$A000-$BFFF  (40960-49151): BASIC ROM (8K)
$C000-$CFFF  (49152-53247): RAM libera (4K)
$D000-$DFFF  (53248-57343): I/O e Color RAM
  $D000-$D02E: VIC-II (chip grafico)
  $D400-$D41C: SID (chip audio)
  $D800-$DBE7: Color RAM
  $DC00-$DC0F: CIA #1 (tastiera, joystick)
  $DD00-$DD0F: CIA #2 (porte seriale, user)
$E000-$FFFF  (57344-65535): KERNAL ROM (8K)
```

## Registri interni del microprocessore 6510

### Registri principali (8 bit ciascuno)

| Registro | Descrizione |
|----------|-------------|
| **A** (Accumulator) | Registro principale per operazioni aritmetiche e logiche |
| **X** | Registro indice, usato per indirizzamento indicizzato |
| **Y** | Registro indice, usato per indirizzamento indicizzato |
| **SP** (Stack Pointer) | Punta alla posizione corrente dello stack ($0100-$01FF) |
| **PC** (Program Counter) | Contatore programma (16 bit), indirizzo istruzione corrente |
| **P** (Processor Status) | Registro stato con flag condizionali |

### Flag del registro stato (P)

| Bit | Flag | Descrizione |
|-----|------|-------------|
| 0 | C (Carry) | Riporto/borrow nelle operazioni aritmetiche |
| 1 | Z (Zero) | Risultato zero |
| 2 | I (Interrupt) | Interrupt disabilitati quando = 1 |
| 3 | D (Decimal) | Modalità decimale quando = 1 |
| 4 | B (Break) | Settato dall'istruzione BRK |
| 5 | - | Non usato (sempre 1) |
| 6 | V (Overflow) | Overflow aritmetico |
| 7 | N (Negative) | Bit 7 del risultato = 1 |

## Come scrivere programmi in linguaggio macchina

### 64MON (Monitor)

Il monitor permette di:
- Visualizzare e modificare la memoria
- Inserire codice macchina
- Eseguire programmi
- Debuggare

### Notazione esadecimale

Il sistema esadecimale (base 16) è usato per rappresentare indirizzi e dati:

| Decimale | Esadecimale |
|----------|-------------|
| 0-9 | $0-$9 |
| 10 | $A |
| 11 | $B |
| 12 | $C |
| 13 | $D |
| 14 | $E |
| 15 | $F |
| 16 | $10 |
| 255 | $FF |
| 256 | $100 |
| 4096 | $1000 |
| 65535 | $FFFF |

### La prima istruzione in linguaggio macchina

**LDA** (Load Accumulator) - Carica il registro A:
```
LDA #$00     ; Carica 0 in A (immediato)
LDA $00      ; Carica il contenuto dell'indirizzo $00 in A (zero page)
```

### Scrivere il primo programma

Esempio: Pulire lo schermo in linguaggio macchina

```
$C000  A9 20     LDA #$20    ; Carica spazio (codice $20)
$C002  A2 00     LDX #$00    ; Inizializza X a 0
$C004  9D 00 04  STA $0400,X ; Memorizza spazio in Screen Memory
$C007  E8        INX         ; Incrementa X
$C008  D0 FA     BNE $C004   ; Salta indietro se X <> 0
$C00A  60        RTS         ; Ritorna
```

## Modalità di indirizzamento

### Zero Page ($00-$FF)
- Indirizzamento a 1 byte
- Più veloce
- Esempio: `LDA $50` (carica da indirizzo $0050)

### Assoluto ($0000-$FFFF)
- Indirizzamento a 2 byte
- Esempio: `LDA $0400` (carica da indirizzo $0400)

### Immediato
- Operando è il valore stesso
- Esempio: `LDA #$20` (carica il valore $20)

### Indicizzato
- Indirizzo base + registro X o Y
- Esempio: `LDA $0400,X` (carica da $0400 + X)

### Indirect Indexed (Indirect,Y)
- Indirizzo in zero page + Y
- Esempio: `LDA ($50),Y`

### Indexed Indirect (Indirect,X)
- Indirizzo in zero page + X
- Esempio: `LDA ($50,X)`

## Lo Stack

- Area memoria $0100-$01FF
- Gestito dal registro SP (Stack Pointer)
- Cresce verso il basso ($FF → $00)
- Usato per:
  - Salvare indirizzi di ritorno (JSR/RTS)
  - Salvare registri (PHA/PLA)

### Istruzioni stack
- **PHA** - Push Accumulator sullo stack
- **PLA** - Pull Accumulator dallo stack
- **PHP** - Push Processor Status
- **PLP** - Pull Processor Status
- **TSX** - Transfer SP to X
- **TXS** - Transfer X to SP

## Salti condizionali e test

### Istruzioni di salto
- **JMP** - Salto incondizionato
- **JSR** - Jump to Subroutine
- **RTS** - Return from Subroutine
- **RTI** - Return from Interrupt

### Salti condizionali (branch)
Tutti i salti condizionali usano offset relativo (-128 a +127):

| Istruzione | Condizione | Flag testato |
|------------|------------|--------------|
| BCC | Branch if Carry Clear | C = 0 |
| BCS | Branch if Carry Set | C = 1 |
| BEQ | Branch if Equal | Z = 1 |
| BNE | Branch if Not Equal | Z = 0 |
| BMI | Branch if Minus | N = 1 |
| BPL | Branch if Plus | N = 0 |
| BVC | Branch if Overflow Clear | V = 0 |
| BVS | Branch if Overflow Set | V = 1 |

### Istruzioni di confronto
- **CMP** - Compare with A
- **CPX** - Compare with X
- **CPY** - Compare with Y

## Subroutine

### JSR (Jump to Subroutine)
```
JSR $C000   ; Salta alla subroutine a $C000
            ; Salva PC+2 sullo stack
```

### RTS (Return from Subroutine)
```
RTS         ; Recupera PC dallo stack e ritorna
```

### Esempio subroutine
```
; Programma principale
$C000  20 05 C0  JSR $C005   ; Chiama subroutine
$C003  00        BRK         ; Fine

; Subroutine
$C005  A9 01     LDA #$01    ; Carica 1 in A
$C007  60        RTS         ; Ritorna
```

## Gestione memoria sul Commodore 64

### Configurazione memoria
Il registro $01 (6510 Port) controlla la configurazione memoria:

| Bit | Funzione |
|-----|----------|
| 0 | LORAM (BASIC ROM) |
| 1 | HIRAM (KERNAL ROM) |
| 2 | CHAREN (I/O / Character ROM) |
| 3 | Cassette motor control |
| 4 | Cassette switch sense |
| 5 | Cassette data output |

### Configurazioni comuni
- **BASIC attivo**: LORAM=1, HIRAM=1, CHAREN=1 → $01 = $27
- **Tutta RAM**: LORAM=0, HIRAM=0, CHAREN=0 → $01 = $00
- **KERNAL + I/O**: LORAM=0, HIRAM=1, CHAREN=1 → $01 = $26

## Il KERNAL

Il KERNAL è il sistema operativo del C64 contenuto in ROM ($E000-$FFFF).

### Attività all'accensione
1. Inizializzazione hardware
2. Test RAM
3. Impostazione vettori interrupt
4. Messaggio di startup

### Come usare il KERNAL

#### Chiamare routine KERNAL
```basic
SYS indirizzo
```

#### Routine KERNAL chiamabili dall'utente

| Nome | Indirizzo | Descrizione |
|------|-----------|-------------|
| CINT | $FF81 | Inizializza schermo |
| IOINIT | $FF84 | Inizializza I/O |
| RAMTAS | $FF87 | Inizializza RAM |
| RESTOR | $FF8A | Ripristina vettori |
| VECTOR | $FF8D | Legge/imposta vettori |
| SETMSG | $FF90 | Imposta messaggi |
| SECOND | $FF93 | Invia second address seriale |
| TKSA | $FF96 | Invia second address seriale (talk) |
| MEMTOP | $FF99 | Legge/imposta top memoria |
| MEMBOT | $FF9C | Legge/imposta bottom memoria |
| SCNKEY | $FF9F | Scansiona tastiera |
| SETTMO | $FFA2 | Imposta timeout seriale |
| ACPTR | $FFA5 | Ricevi byte da seriale |
| CIOUT | $FFA8 | Invia byte su seriale |
| UNTLK | $FFAB | Untalk seriale |
| UNLSN | $FFAE | Unlisten seriale |
| LISTEN | $FFB1 | Comando listen seriale |
| TALK | $FFB4 | Comando talk seriale |
| READST | $FFB7 | Leggi stato I/O |
| SETLFS | $FFBA | Imposta file logico |
| SETNAM | $FFBD | Imposta nome file |
| OPEN | $FFC0 | Apri file |
| CLOSE | $FFC3 | Chiudi file |
| CHKIN | $FFC6 | Imposta input channel |
| CHKOUT | $FFC9 | Imposta output channel |
| CLRCHN | $FFCC | Ripristina canali I/O |
| CHRIN | $FFCF | Input carattere |
| CHROUT | $FFD2 | Output carattere |
| LOAD | $FFD5 | Carica da disco/nastro |
| SAVE | $FFD8 | Salva su disco/nastro |
| SETTIM | $FFDB | Imposta timer sistema |
| RDTIM | $FFDE | Leggi timer sistema |
| STOP | $FFE1 | Controlla tasto STOP |
| GETIN | $FFE4 | Leggi tastiera buffer |
| CLALL | $FFE7 | Chiudi tutti i file |
| UDTIM | $FFEA | Aggiorna timer |
| SCREEN | $FFED | Leggi dimensioni schermo |
| PLOT | $FFF0 | Leggi/imposta posizione cursore |
| IOBASE | $FFF3 | Leggi indirizzo base I/O |

### Codici errore KERNAL

| Codice | Errore |
|--------|--------|
| 0 | OK |
| 1 | Too many files |
| 2 | File open |
| 3 | File not open |
| 4 | File not found |
| 5 | Device not present |
| 6 | Not input file |
| 7 | Not output file |
| 8 | Missing filename |
| 9 | Illegal device number |

## Usare linguaggio macchina dal BASIC

### Dove mettere le routine
- **$C000-$CFFF** (49152-53247): RAM libera, sicura
- **$033C-$03FB** (828-1019): Cassette buffer
- **$02A7-$02FF** (679-767): Area libera

### Come inserire linguaggio macchina

#### Metodo 1: POKE
```basic
10 FOR I=49152 TO 49160
20 READ A:POKE I,A
30 NEXT I
40 DATA 169,1,141,0,4,96
50 SYS 49152
```

#### Metodo 2: Da assembler
- Usare monitor/assember esterno
- Caricare file binario

### Esempio completo
```basic
10 REM CLEAR SCREEN IN MACHINE LANGUAGE
20 FOR I=49152 TO 49161
30 READ A:POKE I,A
40 NEXT I
50 DATA 169,32,162,0,157,0,4,232,208,250,96
60 SYS 49152
70 END
```

## Mappa memoria completa del Commodore 64

### Zero Page ($00-$FF)

| Indirizzo | Descrizione |
|-----------|-------------|
| $00-$01 | 6510 Port direction / Data |
| $02-$03 | Area libera |
| $04-$08 | Area libera (cassette) |
| $09-$0A | Area libera |
| $0B-$0C | Area libera (cassette) |
| $0D-$0F | Area libera |
| $10-$11 | Area libera (cassette) |
| $12-$13 | Area libera |
| $14-$15 | Area libera (cassette) |
| $16-$17 | Area libera |
| $18-$19 | Area libera (cassette) |
| $1A-$21 | Area libera |
| $22-$25 | Cassette buffer pointer |
| $26-$2A | Area libera |
| $2B-$2C | Start BASIC pointer |
| $2D-$2E | Start variables pointer |
| $2F-$30 | Start arrays pointer |
| $31-$32 | End arrays pointer |
| $33-$34 | String pointer (descending) |
| $35-$36 | Utility pointer |
| $37-$38 | End memory pointer |
| $39-$3A | Current line number |
| $3B-$3C | Previous line number |
| $3D-$3E | BASIC statement pointer |
| $3F-$40 | Current DATA line |
| $41-$42 | Current DATA address |
| $43-$44 | Input pointer |
| $45-$46 | Name pointer |
| $47-$48 | Area libera |
| $49-$4A | Area libera |
| $4B-$4C | Area libera |
| $4D-$4E | Area libera |
| $4F-$50 | Area libera |
| $51-$52 | Floating point accumulator 1 (FAC1) |
| $53-$54 | Floating point accumulator 2 (FAC2) |
| $55-$5A | Area libera |
| $5B-$5C | Area libera |
| $5D-$60 | Area libera |
| $61-$66 | Floating point accumulator 1 (FAC1) |
| $67-$6C | Floating point accumulator 2 (FAC2) |
| $6D-$72 | Area libera |
| $73-$8A | CHRGET subroutine |
| $8B-$8F | Area libera |
| $90 | KERNAL status word ST |
| $91 | Stop key flag |
| $92 | Timing constant |
| $93 | Load/verify flag |
| $94 | Serial bus output buffer |
| $95 | Serial bus input buffer |
| $96 | Serial bus byte buffer |
| $97-$9A | Area libera |
| $9B-$9F | Area libera |
| $A0-$A2 | Jiffy clock |
| $A3-$A4 | Area libera |
| $A5-$A6 | Area libera |
| $A7 | Cassette sync count |
| $A8 | Cassette byte count |
| $A9 | Cassette bit count |
| $AA | Cassette start bit flag |
| $AB | Cassette byte buffer |
| $AC-$AD | Cassette buffer pointer |
| $AE-$AF | Cassette end pointer |
| $B0-$B1 | Cassette timing |
| $B2-$B3 | Cassette timing |
| $B4 | Cassette timer 1 |
| $B5 | Cassette timer 2 |
| $B6 | Cassette timer 3 |
| $B7 | Length filename |
| $B8 | Logical file number |
| $B9 | Secondary address |
| $BA | Device number |
| $BB-$BC | Filename pointer |
| $BD | Serial output byte |
| $BE | Cassette motor interlock |
| $BF | Cassette write shift register |
| $C0 | Cassette read shift register |
| $C1-$C2 | Tape start address |
| $C3-$C4 | Tape end address |
| $C5 | Keyboard matrix pointer |
| $C6 | Keyboard buffer count |
| $C7 | Reverse flag |
| $C8 | End line for input |
| $C9 | Cursor log (row) |
| $CA | Cursor log (column) |
| $CB | Key image |
| $CC | Cursor blink enable |
| $CD | Cursor timing |
| $CE | Character under cursor |
| $CF | Cursor blink phase |
| $D0 | Input from screen flag |
| $D1-$D2 | Screen line pointer |
| $D3 | Cursor column |
| $D4 | Cursor row |
| $D5 | Screen line length |
| $D6 | Screen row count |
| $D7 | Character color |
| $D8 | Color under cursor |
| $D9-$F0 | Screen line addresses (low byte) |
| $F1-$F2 | Color RAM line addresses (low byte) |
| $F3-$F4 | Keyboard buffer pointer |
| $F5-$F6 | Area libera |
| $F7-$F8 | RS-232 input buffer pointer |
| $F9-$FA | RS-232 output buffer pointer |
| $FB-$FE | Area libera |
| $FF | BASIC floating point rounding |

### I/O Assignments ($D000-$DFFF)

| Indirizzo | Chip | Registro | Descrizione |
|-----------|------|----------|-------------|
| $D000 | VIC-II | SP0X | Sprite 0 X |
| $D001 | VIC-II | SP0Y | Sprite 0 Y |
| $D002 | VIC-II | SP1X | Sprite 1 X |
| $D003 | VIC-II | SP1Y | Sprite 1 Y |
| $D004 | VIC-II | SP2X | Sprite 2 X |
| $D005 | VIC-II | SP2Y | Sprite 2 Y |
| $D006 | VIC-II | SP3X | Sprite 3 X |
| $D007 | VIC-II | SP3Y | Sprite 3 Y |
| $D008 | VIC-II | SP4X | Sprite 4 X |
| $D009 | VIC-II | SP4Y | Sprite 4 Y |
| $D00A | VIC-II | SP5X | Sprite 5 X |
| $D00B | VIC-II | SP5Y | Sprite 5 Y |
| $D00C | VIC-II | SP6X | Sprite 6 X |
| $D00D | VIC-II | SP6Y | Sprite 6 Y |
| $D00E | VIC-II | SP7X | Sprite 7 X |
| $D00F | VIC-II | SP7Y | Sprite 7 Y |
| $D010 | VIC-II | MSIGX | MSB sprite X |
| $D011 | VIC-II | SCROLY | Control register 1 |
| $D012 | VIC-II | RASTER | Raster line |
| $D013 | VIC-II | LPENX | Light pen X |
| $D014 | VIC-II | LPENY | Light pen Y |
| $D015 | VIC-II | SPENA | Sprite enable |
| $D016 | VIC-II | SCROLX | Control register 2 |
| $D017 | VIC-II | YXPAND | Sprite Y expand |
| $D018 | VIC-II | VMCSB | Memory pointers |
| $D019 | VIC-II | VICIRQ | Interrupt register |
| $D01A | VIC-II | IRQMASK | Interrupt enabled |
| $D01B | VIC-II | SPBGPR | Sprite priority |
| $D01C | VIC-II | SPMC | Sprite multicolor |
| $D01D | VIC-II | XXPAND | Sprite X expand |
| $D01E | VIC-II | SPSPCL | Sprite-sprite collision |
| $D01F | VIC-II | SPBGCL | Sprite-background collision |
| $D020 | VIC-II | EXTCOL | Border color |
| $D021 | VIC-II | BGCOL0 | Background color 0 |
| $D022 | VIC-II | BGCOL1 | Background color 1 |
| $D023 | VIC-II | BGCOL2 | Background color 2 |
| $D024 | VIC-II | BGCOL3 | Background color 3 |
| $D025 | VIC-II | SPMC0 | Sprite multicolor 0 |
| $D026 | VIC-II | SPMC1 | Sprite multicolor 1 |
| $D027 | VIC-II | SP0COL | Sprite 0 color |
| $D028 | VIC-II | SP1COL | Sprite 1 color |
| $D029 | VIC-II | SP2COL | Sprite 2 color |
| $D02A | VIC-II | SP3COL | Sprite 3 color |
| $D02B | VIC-II | SP4COL | Sprite 4 color |
| $D02C | VIC-II | SP5COL | Sprite 5 color |
| $D02D | VIC-II | SP6COL | Sprite 6 color |
| $D02E | VIC-II | SP7COL | Sprite 7 color |
| $D400 | SID | FRELO1 | Voice 1 frequency low |
| $D401 | SID | FREHI1 | Voice 1 frequency high |
| $D402 | SID | PWLO1 | Voice 1 pulse width low |
| $D403 | SID | PWHI1 | Voice 1 pulse width high |
| $D404 | SID | VCREG1 | Voice 1 control |
| $D405 | SID | ATDCY1 | Voice 1 attack/decay |
| $D406 | SID | SUREL1 | Voice 1 sustain/release |
| $D407 | SID | FRELO2 | Voice 2 frequency low |
| $D408 | SID | FREHI2 | Voice 2 frequency high |
| $D409 | SID | PWLO2 | Voice 2 pulse width low |
| $D40A | SID | PWHI2 | Voice 2 pulse width high |
| $D40B | SID | VCREG2 | Voice 2 control |
| $D40C | SID | ATDCY2 | Voice 2 attack/decay |
| $D40D | SID | SUREL2 | Voice 2 sustain/release |
| $D40E | SID | FRELO3 | Voice 3 frequency low |
| $D40F | SID | FREHI3 | Voice 3 frequency high |
| $D410 | SID | PWLO3 | Voice 3 pulse width low |
| $D411 | SID | PWHI3 | Voice 3 pulse width high |
| $D412 | SID | VCREG3 | Voice 3 control |
| $D413 | SID | ATDCY3 | Voice 3 attack/decay |
| $D414 | SID | SUREL3 | Voice 3 sustain/release |
| $D415 | SID | CUTLO | Filter cutoff low |
| $D416 | SID | CUTHI | Filter cutoff high |
| $D417 | SID | RESON | Filter resonance/voice |
| $D418 | SID | SIGVOL | Volume/filter mode |
| $D419 | SID | POTX | Paddle X |
| $D41A | SID | POTY | Paddle Y |
| $D41B | SID | RANDOM | Oscillator 3 random |
| $D41C | SID | ENV3 | Envelope generator 3 |
| $DC00 | CIA #1 | PRA | Port A (tastiera, joystick 2) |
| $DC01 | CIA #1 | PRB | Port B (tastiera, joystick 1) |
| $DC02 | CIA #1 | DDRA | Data direction A |
| $DC03 | CIA #1 | DDRB | Data direction B |
| $DC04 | CIA #1 | TA LO | Timer A low |
| $DC05 | CIA #1 | TA HI | Timer A high |
| $DC06 | CIA #1 | TB LO | Timer B low |
| $DC07 | CIA #1 | TB HI | Timer B high |
| $DC08 | CIA #1 | TOD 10TH | Time of day 10ths |
| $DC09 | CIA #1 | TOD SEC | Time of day seconds |
| $DC0A | CIA #1 | TOD MIN | Time of day minutes |
| $DC0B | CIA #1 | TOD HR | Time of day hours |
| $DC0C | CIA #1 | SDR | Serial data register |
| $DC0D | CIA #1 | ICR | Interrupt control |
| $DC0E | CIA #1 | CRA | Control A |
| $DC0F | CIA #1 | CRB | Control B |
| $DD00 | CIA #2 | PRA | Port A (serial bus, VIC bank) |
| $DD01 | CIA #2 | PRB | Port B (RS-232, user port) |
| $DD02 | CIA #2 | DDRA | Data direction A |
| $DD03 | CIA #2 | DDRB | Data direction B |
| $DD04 | CIA #2 | TA LO | Timer A low |
| $DD05 | CIA #2 | TA HI | Timer A high |
| $DD06 | CIA #2 | TB LO | Timer B low |
| $DD07 | CIA #2 | TB HI | Timer B high |
| $DD08 | CIA #2 | TOD 10TH | Time of day 10ths |
| $DD09 | CIA #2 | TOD SEC | Time of day seconds |
| $DD0A | CIA #2 | TOD MIN | Time of day minutes |
| $DD0B | CIA #2 | TOD HR | Time of day hours |
| $DD0C | CIA #2 | SDR | Serial data register |
| $DD0D | CIA #2 | ICR | Interrupt control |
| $DD0E | CIA #2 | CRA | Control A |
| $DD0F | CIA #2 | CRB | Control B |

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

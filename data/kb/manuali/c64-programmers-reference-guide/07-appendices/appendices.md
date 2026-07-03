---
title: "Appendici"
description: "Appendici tecniche del Commodore 64 Programmer's Reference Guide"
tags: [c64, reference, appendices, codes, maps, specifications]
source: "Commodore 64 Programmer's Reference Guide, Appendices"
---

# Appendici

## A. Abbreviazioni per keyword BASIC

| Keyword | Abbreviazione | Tasto |
|---------|--------------|-------|
| ABS | A | SHIFT+B |
| AND | A | SHIFT+N |
| ASC | A | SHIFT+S |
| ATN | A | SHIFT+T |
| CHR$ | C | SHIFT+H |
| CLOSE | CL | SHIFT+O |
| CLR | C | SHIFT+L |
| CMD | C | SHIFT+M |
| CONT | C | SHIFT+O |
| COS | C | SHIFT+O |
| DATA | D | SHIFT+A |
| DEF | D | SHIFT+E |
| DIM | D | SHIFT+I |
| END | E | SHIFT+N |
| EXP | E | SHIFT+X |
| FN | F | SHIFT+N |
| FOR | F | SHIFT+O |
| FRE | F | SHIFT+R |
| GET | G | SHIFT+E |
| GET# | G | SHIFT+E |
| GOSUB | GO | SHIFT+S |
| GOTO | G | SHIFT+O |
| IF | I | SHIFT+F |
| INPUT | I | SHIFT+N |
| INPUT# | I | SHIFT+N |
| INT | I | SHIFT+N |
| LEFT$ | LE | SHIFT+F |
| LEN | L | SHIFT+E |
| LET | L | SHIFT+E |
| LIST | L | SHIFT+I |
| LOAD | L | SHIFT+O |
| LOG | L | SHIFT+O |
| MID$ | M | SHIFT+I |
| NEW | N | SHIFT+E |
| NEXT | N | SHIFT+E |
| NOT | N | SHIFT+O |
| ON | O | SHIFT+N |
| OPEN | O | SHIFT+P |
| OR | O | SHIFT+R |
| PEEK | P | SHIFT+E |
| π (PI) | P | SHIFT+I |
| POKE | P | SHIFT+O |
| POS | P | SHIFT+O |
| PRINT | ? | (tasto ?) |
| PRINT# | P | SHIFT+R |
| READ | R | SHIFT+E |
| REM | R | SHIFT+E |
| RESTORE | RE | SHIFT+S |
| RETURN | RE | SHIFT+T |
| RIGHT$ | R | SHIFT+I |
| RND | R | SHIFT+N |
| RUN | R | SHIFT+U |
| SAVE | S | SHIFT+A |
| SGN | S | SHIFT+G |
| SIN | S | SHIFT+I |
| SPC | S | SHIFT+P |
| SQR | S | SHIFT+Q |
| STEP | ST | SHIFT+E |
| STOP | S | SHIFT+T |
| STR$ | ST | SHIFT+R |
| SYS | S | SHIFT+Y |
| TAB | T | SHIFT+A |
| TAN | T | SHIFT+A |
| THEN | T | SHIFT+H |
| TIME (TI) | T | SHIFT+I |
| TIME$ (TI$) | T | SHIFT+I |
| TO | T | SHIFT+O |
| USR | U | SHIFT+S |
| VAL | V | SHIFT+A |
| VERIFY | V | SHIFT+E |
| WAIT | W | SHIFT+A |

## B. Screen Display Codes

### Codici carattere standard (Set 1)

| Codice | Carattere | Codice | Carattere |
|--------|-----------|--------|-----------|
| 0 | @ | 32 | spazio |
| 1 | A | 33 | ! |
| 2 | B | 34 | " |
| 3 | C | 35 | # |
| 4 | D | 36 | $ |
| 5 | E | 37 | % |
| 6 | F | 38 | & |
| 7 | G | 39 | ' |
| 8 | H | 40 | ( |
| 9 | I | 41 | ) |
| 10 | J | 42 | * |
| 11 | K | 43 | + |
| 12 | L | 44 | , |
| 13 | M | 45 | - |
| 14 | N | 46 | . |
| 15 | O | 47 | / |
| 16 | P | 48 | 0 |
| 17 | Q | 49 | 1 |
| 18 | R | 50 | 2 |
| 19 | S | 51 | 3 |
| 20 | T | 52 | 4 |
| 21 | U | 53 | 5 |
| 22 | V | 54 | 6 |
| 23 | W | 55 | 7 |
| 24 | X | 56 | 8 |
| 25 | Y | 57 | 9 |
| 26 | Z | 58 | : |
| 27 | [ | 59 | ; |
| 28 | £ | 60 | < |
| 29 | ] | 61 | = |
| 30 | ↑ | 62 | > |
| 31 | ← | 63 | ? |

### Codici colore

| Codice | Colore |
|--------|--------|
| 0 | Nero |
| 1 | Bianco |
| 2 | Rosso |
| 3 | Ciano |
| 4 | Viola |
| 5 | Verde |
| 6 | Blu |
| 7 | Giallo |
| 8 | Arancione |
| 9 | Marrone |
| 10 | Rosa chiaro |
| 11 | Grigio scuro |
| 12 | Grigio medio |
| 13 | Verde chiaro |
| 14 | Azzurro chiaro |
| 15 | Grigio chiaro |

## C. ASCII e CHR$ Codes

### CHR$ codes utili

| CHR$(n) | Funzione |
|---------|----------|
| CHR$(0) | Null |
| CHR$(7) | Bell |
| CHR$(8) | Backspace (DEL) |
| CHR$(9) | Tab orizzontale |
| CHR$(10) | Line feed |
| CHR$(13) | Carriage return |
| CHR$(14) | Switch to lower case |
| CHR$(17) | Cursore giù |
| CHR$(18) | Reverse on |
| CHR$(19) | Home |
| CHR$(20) | Delete |
| CHR$(29) | Cursore destra |
| CHR$(141) | Shift+Return |
| CHR$(142) | Switch to upper case |
| CHR$(144) | Black |
| CHR$(145) | Cursore su |
| CHR$(146) | Reverse off |
| CHR$(147) | Clear screen |
| CHR$(148) | Insert |
| CHR$(149) | Brown |
| CHR$(150) | Cursore sinistra |
| CHR$(151) | Grigio scuro |
| CHR$(152) | Grigio medio |
| CHR$(153) | Verde chiaro |
| CHR$(154) | Azzurro chiaro |
| CHR$(155) | Grigio chiaro |
| CHR$(156) | Viola |
| CHR$(157) | Cursore sinistra |
| CHR$(158) | Giallo |
| CHR$(159) | Ciano |
| CHR$(160) | Shift+spazio |

## D. Screen e Color Memory Maps

### Screen Memory ($0400-$07FF)

```
Riga 0:  $0400-$0427 (1024-1063)
Riga 1:  $0428-$044F (1064-1103)
Riga 2:  $0450-$0477 (1104-1143)
Riga 3:  $0478-$049F (1144-1183)
Riga 4:  $04A0-$04C7 (1184-1223)
Riga 5:  $04C8-$04EF (1224-1263)
Riga 6:  $04F0-$0517 (1264-1303)
Riga 7:  $0518-$053F (1304-1343)
Riga 8:  $0540-$0567 (1344-1383)
Riga 9:  $0568-$058F (1384-1423)
Riga 10: $0590-$05B7 (1424-1463)
Riga 11: $05B8-$05DF (1464-1503)
Riga 12: $05E0-$0607 (1504-1543)
Riga 13: $0608-$062F (1544-1583)
Riga 14: $0630-$0657 (1584-1623)
Riga 15: $0658-$067F (1624-1663)
Riga 16: $0680-$06A7 (1664-1703)
Riga 17: $06A8-$06CF (1704-1743)
Riga 18: $06D0-$06F7 (1744-1783)
Riga 19: $06F8-$071F (1784-1823)
Riga 20: $0720-$0747 (1824-1863)
Riga 21: $0748-$076F (1864-1903)
Riga 22: $0770-$0797 (1904-1943)
Riga 23: $0798-$07BF (1944-1983)
Riga 24: $07C0-$07E7 (1984-2023)
```

### Color Memory ($D800-$DBE7)

```
Riga 0:  $D800-$D827 (55296-55319)
Riga 1:  $D828-$D84F (55320-55351)
... (stessa struttura di Screen Memory)
Riga 24: $DBC0-$DBE7 (56256-56287)
```

## E. Valori note musicali

### Frequenze SID per note (approximative)

| Nota | Frequenza (Hz) | Registro SID |
|------|----------------|--------------|
| C0 | 16.35 | ~$0116 |
| C#0 | 17.32 | ~$0127 |
| D0 | 18.35 | ~$0139 |
| D#0 | 19.45 | ~$014C |
| E0 | 20.60 | ~$0161 |
| F0 | 21.83 | ~$0176 |
| F#0 | 23.12 | ~$018D |
| G0 | 24.50 | ~$01A5 |
| G#0 | 25.96 | ~$01BF |
| A0 | 27.50 | ~$01DA |
| A#0 | 29.14 | ~$01F7 |
| B0 | 30.87 | ~$0216 |
| C1 | 32.70 | ~$022D |
| C4 (Do centrale) | 261.63 | ~$1164 |
| A4 (La 440Hz) | 440.00 | ~$1C1F |

### Ottave complete

Il SID copre 9 ottave complete (C0 a B8).
Per i valori esatti di tutte le note, consultare la tabella completa nel manuale originale.

## F. Bibliografia

Risorse consigliate per approfondimenti:
- Manuali Commodore originali
- Riviste: POWER/PLAY, COMMODORE Magazine
- Commodore Information Network su CompuServe
- Club utenti Commodore locali

## G. VIC Chip Register Map

Vedi Capitolo 3 (Graphics) e Capitolo 5 (Machine Language) per la mappa completa dei registri VIC-II.

## H. Derivazione funzioni matematiche

Funzioni matematiche derivabili in BASIC:

| Funzione | Derivazione |
|----------|-------------|
| SEC(X) | =1/COS(X) |
| CSC(X) | =1/SIN(X) |
| COT(X) | =1/TAN(X) |
| ASN(X) | =ATN(X/SQR(-X*X+1)) |
| ACS(X) | =-ATN(X/SQR(-X*X+1))+π/2 |
| LOG10(X) | =LOG(X)/LOG(10) |
| LOG2(X) | =LOG(X)/LOG(2) |

## I. Pinout per dispositivi I/O

### Connettore seriale (DIN 6-pin)
Vedi sezione "Serial Bus" nel Capitolo 6.

### Connettore cassette (DIN 6-pin)
| Pin | Funzione |
|-----|----------|
| 1 | Motor control |
| 2 | GND |
| 3 | Motor control |
| 4 | Data input |
| 5 | Data output |
| 6 | Data input |

### Connettore User Port (24 pin)
Vedi sezione "User Port" nel Capitolo 6.

## J. Conversione BASIC standard a C64 BASIC

Differenze principali:
- C64 usa solo i primi 2 caratteri significativi per i nomi variabili
- Stringhe racchiuse in doppie virgolette
- Comandi specifici C64: POKE, PEEK, SYS
- Assenza di alcuni comandi estesi (STRING$, SPACE$, etc.)

## K. Messaggi di errore

| Messaggio | Descrizione |
|-----------|-------------|
| ?BAD SUBSCRIPT | Indice array fuori range |
| ?CAN'T CONTINUE | Impossibile continuare dopo STOP/END |
| ?DEVICE NOT PRESENT | Periferica non collegata |
| ?DIVISION BY ZERO | Divisione per zero |
| ?FILE NOT FOUND | File non trovato |
| ?FILE NOT OPEN | File non aperto |
| ?FILE OPEN | File già aperto |
| ?FORMULA TOO COMPLEX | Espressione troppo complessa |
| ?ILLEGAL DIRECT | Comando non permesso in modalità diretta |
| ?ILLEGAL QUANTITY | Valore fuori range |
| ?NEXT WITHOUT FOR | NEXT senza FOR corrispondente |
| ?OUT OF DATA | Dati insufficienti in READ/DATA |
| ?OUT OF MEMORY | Memoria esaurita |
| ?OVERFLOW | Risultato troppo grande |
| ?REDIM'D ARRAY | Array già dimensionato |
| ?RETURN WITHOUT GOSUB | RETURN senza GOSUB |
| ?STRING TOO LONG | Stringa > 255 caratteri |
| ?SYNTAX ERROR | Errore di sintassi |
| ?TOO MANY FILES | Troppi file aperti |
| ?TYPE MISMATCH | Tipo dati non compatibile |
| ?UNDEF'D FUNCTION | Funzione non definita |
| ?UNDEF'D STATEMENT | Linea non esistente |
| ?VERIFY ERROR | Errore di verifica |

## L. Specifiche chip 6510

### Microprocessore MOS 6510
- Architettura: 8-bit
- Clock: 0.985 MHz (PAL) / 1.023 MHz (NTSC)
- Indirizzamento: 16 bit (64KB)
- Istruzioni: 56 istruzioni, 13 modalità indirizzamento
- Stack: 256 byte ($0100-$01FF)
- Interrupt: NMI, IRQ, RESET
- Porta I/O integrata (6 bit)

## M. Specifiche chip 6526 (CIA)

### Complex Interface Adapter
- Due timer a 16 bit (A e B)
- Time-of-Day clock (TOD)
- Porte parallele (8 bit ciascuna)
- Registro shift seriale
- Controllo interrupt

## N. Specifiche chip 6566/6567 (VIC-II)

### Video Interface Chip II
- Risoluzione: 320×200 (hi-res) / 160×200 (multi-color)
- Colori: 16
- Sprite: 8 hardware
- Modalità: carattere, bitmap, multi-color
- Smooth scrolling
- Interrupt raster

## O. Specifiche chip 6581 (SID)

### Sound Interface Device
- 3 voci indipendenti
- 4 forme d'onda: triangle, sawtooth, pulse, noise
- ADSR envelope generator per voce
- Filtro programmabile (low-pass, band-pass, high-pass)
- Ring modulation e synchronization
- 9 ottave
- Uscita audio mono

## P. Glossario

| Termine | Definizione |
|---------|-------------|
| Accumulator | Registro principale del processore |
| Address | Indirizzo di memoria |
| Array | Tabella di elementi dati |
| ASCII | American Standard Code for Information Interchange |
| Bit | Cifra binaria (0 o 1) |
| Byte | 8 bit |
| Cartridge | Modulo ROM espandibile |
| CIA | Complex Interface Adapter |
| CPU | Central Processing Unit |
| CRT | Cathode Ray Tube (tubo catodico) |
| DMA | Direct Memory Access |
| EPROM | Erasable Programmable ROM |
| I/O | Input/Output |
| IRQ | Interrupt Request |
| KERNAL | Kernel del sistema operativo C64 |
| LSB | Least Significant Bit/Byte |
| MSB | Most Significant Bit/Byte |
| NMI | Non-Maskable Interrupt |
| NTSC | National Television System Committee |
| PAL | Phase Alternating Line |
| Pixel | Picture element |
| RAM | Random Access Memory |
| ROM | Read Only Memory |
| RS-232 | Standard seriale |
| SID | Sound Interface Device |
| Sprite | Oggetto grafico hardware |
| Stack | Area memoria LIFO |
| VIC-II | Video Interface Chip II |
| Zero Page | Prima pagina memoria ($00-$FF) |

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

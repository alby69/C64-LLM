# 6502 Addressing Modes — Modalità di Indirizzamento del 6502

Il 6502 ha 13 modalità di indirizzamento. Capirle è essenziale per programmare il C64 in assembly.

## Tabella Riassuntiva

| # | Modalità | Sintassi | Bytes | Operazione | Esempio |
|---|----------|----------|-------|------------|---------|
| 1 | Implicita | — | 1 | L'operando è implicito nell'istruzione | `INX`, `CLC` |
| 2 | Accumulatore | — | 1 | Opera sull'accumulatore A | `LSR A` |
| 3 | Immediata | `#n` | 2 | Costante immediata | `LDA #$FF` |
| 4 | Assoluta | `addr` | 3 | Indirizzo di memoria a 16 bit | `STA $D020` |
| 5 | Zero Page | `zp` | 2 | Indirizzo pagina zero (0-255) | `LDA $C6` |
| 6 | Indiretta X | `(zp,X)` | 2 | (zp + X) → indirizzo a 16 bit | `LDA ($FA,X)` |
| 7 | Indiretta Y | `(zp),Y` | 2 | (zp) + Y → indirizzo a 16 bit | `LDA ($FA),Y` |
| 8 | X indicizzata | `addr,X` | 3 | addr + X | `LDA $0400,X` |
| 9 | Y indicizzata | `addr,Y` | 3 | addr + Y | `LDA $0400,Y` |
| 10 | ZP X | `zp,X` | 2 | zp + X (pagina zero) | `LDA $C0,X` |
| 11 | ZP Y | `zp,Y` | 2 | zp + Y (pagina zero) | `LDX $C0,Y` |
| 12 | Relativa | `label` | 2 | Branch relativo (±127 byte) | `BEQ loop` |
| 13 | Indiretta | `(addr)` | 3 | Puntatore a 16 bit (solo JMP) | `JMP ($0314)` |

## Dettaglio con Esempi C64

### Implicita
Nessun operando esplicito. L'istruzione stessa determina l'operazione.
```
CLC           ; Azzera carry (C = 0)
SEC           ; Setta carry (C = 1)
INX           ; X = X + 1
DEX           ; X = X - 1
RTS           ; Return from subroutine
```

### Accumulatore
Opera direttamente sul registro A.
```
LSR A         ; Shift a destra di A
ASL A         ; Shift a sinistra di A
ROL A         ; Ruota a sinistra tramite carry
ROR A         ; Ruota a destra tramite carry
```

### Immediata (#)
Il valore (costante) è contenuto nel secondo byte dell'istruzione. NON è un indirizzo.
```
LDA #$00      ; Carica il valore 0 in A (NON l'indirizzo $0000)
LDX #$FF      ; Carica 255 in X
AND #$0F      ; Maschera i 4 bit bassi
ORA #$80      ; Setta bit 7
CMP #$20      ; Confronta con spazio (ASCII 32)
```

### Assoluta
Indirizzo a 16 bit (3 byte totali). Usato per accedere a qualsiasi locazione.
```
STA $D020     ; Scrivi A nel colore bordo
LDA $C000     ; Leggi da $C000
STA $0400     ; Scrivi in screen memory
INC $D021     ; Incrementa colore sfondo
DEC $D020     ; Decrementa colore bordo (effetto flash)
```

### Zero Page
Simile all'assoluta ma solo per i primi 256 byte ($0000-$00FF). Più veloce (2 byte, 3 cicli vs 4).
```
LDA $C6       ; Leggi il contatore tastiera (KERNAL)
STA $FB       ; Salva nella variabile temporanea
LDX $D0       ; Leggi il puntatore BASIC per list
STX $C3       ; Variabile di sistema
```

Il 6502 ha solo 256 byte di zero page. Usatela per variabili frequenti.

### Indiretta X (pre-indicizzata)
Prima somma X all'indirizzo zero page, poi legge l'indirizzo a 16 bit da quella locazione.
```
; Tabella puntatori a 16 bit in ZP
; $FA/$FB = address1, $FC/$FD = address2

      LDX #$02      ; Vuoi il secondo puntatore
      LDA ($FA,X)   ; Legge dall'indirizzo in $FC/$FD
                     ; (perché $FA + 2 = $FC)
```
Utile per array di puntatori.

### Indiretta Y (post-indicizzata)
Legge l'indirizzo a 16 bit dallo zero page, poi ci somma Y.
```
; Legge dati da un indirizzo puntato da $FB/$FC
      LDY #0
loop:
      LDA ($FB),Y   ; Carica byte da ($FB) + Y
      STA $0400,Y   ; Copia in screen
      INY
      CPY #$28      ; 40 colonne
      BNE loop
```
Modalità più usata per leggere array grandi. Veloce perché la ZP page è già nel buffer CPU.

### X/Y Indicizzata (Assoluta)
Somma X o Y all'indirizzo base per ottenere l'indirizzo finale.
```
; Scorrere lo schermo
      LDX #0
loop:
      LDA #$01      ; Colore bianco
      STA $D800,X   ; Color RAM iniziando da $D800
      INX
      CPX #40       ; 40 colonne
      BNE loop

; Leggere una tabella
      LDY #0
loop2:
      LDA tabella,Y
      STA $0400,Y
      INY
      CPY #100
      BNE loop2
```
Attenzione: se l'indirizzo base + X supera $FFFF, c'è wrap-around (bug del 6502!).

### ZP X / ZP Y
Come sopra ma limitato alla pagina zero (indirizzo finale < $0100).
```
      LDX #$00
loop:
      STX $C0,X     ; Azzera area variabili ($C0-$FF)
      INX
      CPX #$40
      BNE loop
```

### Relativa (Branch)
Usata solo per istruzioni di salto condizionato. Lo spiazzamento è signed (-128 a +127 byte).
```
      LDA $D012
      CMP #$FF
      BNE wait       ; Salta se NON uguale (branch)

; Branch lungo: combinazione BNE + JMP
      BNE skip
      JMP far_label  ; Oltre 127 byte
skip:
```

### Indiretta (JMP Solo)
```
      JMP ($0314)    ; Salta all'indirizzo contenuto in $0314/$0315
```
BUG del 6502: Se l'indirizzo finisce con $FF (es. JMP ($01FF)), legge da $01FF e $0100 (non $0200) a causa del wrap-around pagina.

## Tabella Cicli CPU

| Modalità | Cicli | Bytes | Note |
|----------|-------|-------|------|
| Implicita | 2 | 1 | |
| Accumulatore | 2 | 1 | |
| Immediata | 2 | 2 | |
| Assoluta | 4 | 3 | +1 se pagina crossing |
| Zero Page | 3 | 2 | |
| ZP,X | 4 | 2 | |
| ZP,Y | 4 | 2 | (solo LDX/STX) |
| X indicizzata | 4 | 3 | +1 se pagina crossing |
| Y indicizzata | 4 | 3 | +1 se pagina crossing |
| Indiretta X | 6 | 2 | |
| Indiretta Y | 5 | 2 | +1 se pagina crossing |
| Relativa | 2 | 2 | +1 se branch preso, +1 se pagina crossing |

## Consigli Pratici

- **Zero page** per variabili usate spesso: risparmia byte e cicli.
- **Indiretta Y** per array grandi: comoda e veloce.
- **Assoluta** per registri hardware ($D000-$DFFF) — unica scelta.
- **Immediata** per costanti e maschere.
- **Indiretta X** per tabelle di puntatori (es. lista sprite, dati livelli).
- **Evita indiretta X** se non hai una struttura a puntatori — Indiretta Y è più comune.
- **Attenzione al page crossing**: costa un ciclo extra. Se possibile, allinea i dati a $xx00.

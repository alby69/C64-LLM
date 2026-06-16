# KERNAL Routines — Routine del KERNAL C64

Il KERNAL Commodore 64 è un insieme di routine in ROM che forniscono funzioni di base per I/O, schermo, tastiera, cassette, serial bus. Si chiamano con JSR.

## Routine di Schermo

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $E544 | Clear Screen | Pulisce lo schermo e posiziona il cursore in home |
| $E566 | HOME | Sposta il cursore in alto a sinistra senza pulire |
| $E500 | Newline | Va a capo (CR/LF) |
| $E716 | Output Character | Stampa un carattere (A contiene il codice) |
| $E742 | Scroll | Fa scorrere lo schermo in su di una riga |
| $E9FF | Clear Line | Pulisce la riga corrente |
| $E9F4 | Insert Line | Inserisce una riga vuota sotto il cursore |
| $EA13 | Delete Line | Cancella la riga corrente |
| $F129 | PLOT | Legge/imposta posizione cursore (X=col, Y=riga) |
| $F20E | Set Screen Colors | Imposta colore caratteri e sfondo |

### Esempi
```
; Stampa un carattere sullo schermo
      lda #'A'
      jsr $FFD2      ; CHROUT — stampa carattere in A

; Posiziona il cursore a colonna 10, riga 5
      ldx #10        ; colonna
      ldy #5         ; riga
      clc            ; C=0 per impostare posizione
      jsr $FFF0      ; PLOT

; Legge posizione cursore
      sec            ; C=1 per leggere
      jsr $FFF0      ; PLOT; X=colonna, Y=riga
```

## Routine di Tastiera

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $E5B4 | GETIN | Legge un carattere dalla tastiera (A = carattere o 0 se nessun tasto premuto) |
| $F142 | Scan Keyboard | Scansione fisica della tastiera (aggiorna buffer) |
| $F1EA | Wait for Key | Aspetta un tasto (non usare in codice IRQ!) |

### Esempi
```
; Legge un tasto (non bloccante)
      jsr $FFE4      ; GETIN
      cmp #0
      beq no_key

; Aspetta un tasto (bloccante — loop GETIN)
wait_key:
      jsr $FFE4
      cmp #0
      beq wait_key
```

## Routine di I/O (Cassetta / Serial Bus)

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $FFBA | SETNAM | Imposta nome file (A=lunghezza, X/Y=puntatore) |
| $FFBD | SETLFS | Imposta device (A=file#, X=device, Y=comando) |
| $FFD5 | LOAD | Carica file (A=0 per LOAD, 1 per VERIFY, X/Y=puntatore) |
| $FFD8 | SAVE | Salva file (A=0, X/Y=puntatore start, $C3=$AE fine) |
| $FFC6 | CHROUT | Output carattere (A=carattere) |
| $FFC9 | CHRIN | Input carattere (da RS-232 o tape) |
| $FFCF | CLOSE | Chiude file |
| $FFE1 | CLALL | Chiude tutti i file |

### Esempio: Caricare un File
```
; Carica "PROGRAMMA" dal drive 8
      lda #8         ; lunghezza nome
      ldx #<filename ; puntatore al nome
      ldy #>filename
      jsr $FFBA      ; SETNAM

      lda #1         ; file number
      ldx #8         ; device (8 = disk drive)
      ldy #1         ; comando (1 = LOAD)
      jsr $FFBD      ; SETLFS

      lda #0         ; 0 = LOAD (non VERIFY)
      ldx #<$C000    ; indirizzo di caricamento (opzionale)
      ldy #>$C000
      jsr $FFD5      ; LOAD

filename:
      .text "PROGRAMMA"
```

## Routine di Gestione Interrupt

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $EA31 | IRQ Handler | Handler interrupt standard (salva A,X,Y, riconosce, RTI) |
| $EA81 | BRK Handler | Handler per BRK, simile a $EA31 ma per BRK |
| $FE66 | NMI Handler | Handler NMI standard |

## Utility

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $FF81 | RDTIM | Legge orologio (A=ore, X=min, Y=sec) |
| $FF84 | SETTIM | Imposta orologio |
| $FF87 | STTOP | Ferma il nastro |
| $FF8A | UDTIM | Aggiorna orologio |
| $FF8D | RND | Numero casuale (A=seme, restituisce in A) |
| $FF90 | Vectors | Copia vettori dalla ROM alla RAM |
| $FF93 | IOINIT | Inizializza I/O |
| $FF9C | RAMTAS | Test RAM e inizializza |
| $FFF0 | PLOT | Cursore (vedi sopra) |

## Vettori ($0314-$0333)

Questi puntatori in RAM possono essere modificati per intercettare le chiamate KERNAL:

| Indirizzo | Lunghezza | Descrizione |
|-----------|-----------|-------------|
| $0314-5 | 2 | IRQ vector |
| $0316-7 | 2 | BRK vector |
| $0318-9 | 2 | NMI vector |
| $031A-B | 2 | IOPEN (OPEN) |
| $031C-D | 2 | ICLOSE (CLOSE) |
| $031E-F | 2 | ICHRIN (CHRIN) |
| $0320-1 | 2 | ICHROUT (CHROUT) |
| $0322-3 | 2 | ISTOP (STOP) |
| $0324-5 | 2 | IGETIN (GETIN) |
| $0326-7 | 2 | ICLALL (CLALL) |
| $0328-9 | 2 | USRCMD (USR) |
| $032A-B | 2 | ILOAD (LOAD) |
| $032C-D | 2 | ISAVE (SAVE) |

## Note Importanti

- **CHROUT ($FFD2)** è la routine più usata: stampa il carattere in A alla posizione corrente del cursore.
- **GETIN ($FFE4)** non blocca: restituisce 0 se nessun tasto premuto. Per input bloccante, loop in BASIC.
- **LOAD ($FFD5)** con A=0 e X/Y=$C000 carica al destinazione specificata; con X/Y=0 carica all'indirizzo salvato nel file.
- **SETLFS** device 8 = floppy 1541, device 1 = datasette.
- I vettori ($0314-$0333) vanno modificati solo dopo aver copiato la tabella dalla ROM con JSR $FF90.

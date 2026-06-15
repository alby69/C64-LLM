---
title: "Introduzione al BASIC V2"
category: BASIC
tags: [c64, basic, tutorial, fundamentals]
---

## BASIC V2 su Commodore 64

Il BASIC V2 è il linguaggio di programmazione integrato nel Commodore 64. Si trova nella ROM e si avvia automaticamente all'accensione (se non c'è un cartridge inserito).

## Struttura di un programma BASIC

Ogni riga di un programma BASIC inizia con un **numero di riga**, seguito da una o più istruzioni separate da `:` (due punti). Il programma viene eseguito in ordine crescente di numero di riga.

```
10 PRINT "HELLO"
20 INPUT N
30 PRINT N + 5
```

### Numeri di riga
- Vanno da 0 a 63999
- Di solito si usano incrementi di 10 (10, 20, 30...) per permettere inserimenti successivi
- L'ordine di esecuzione è determinato dal numero, non dall'ordine fisico

## Comandi fondamentali

### PRINT
Visualizza testo o valori sullo schermo.

```
10 PRINT "TESTO"
20 PRINT 42
30 PRINT "VALORE:"; X
```
- La virgola (`,`) separa in colonne (ogni 10 caratteri)
- Il punto e virgola (`;`) concatena senza spazi

### INPUT
Legge un valore inserito dall'utente da tastiera.

```
10 INPUT "NOME"; N$
20 INPUT A
```

### Variabili
- **Numeriche**: una lettera (A-Z) o lettera+cifra (A0-Z9)
- **Stringa**: come sopra ma con `$` finale (A$, B5$, N$)
- **Intero**: con `%` finale (A%, C%)
- Esempi: `A = 10`, `N$ = "MARIO"`, `X% = 5`
- Le variabili numeriche valgono 0 se non assegnate
- Le variabili stringa valgono "" (vuota) se non assegnate

### GOTO
Salta a un numero di riga specifico.

```
10 PRINT "CIAO"
20 GOTO 10
```

### IF...THEN
Esecuzione condizionale.

```
10 INPUT A
20 IF A > 10 THEN PRINT "MAGGIORE"
30 IF A = 5 THEN PRINT "CINQUE": GOTO 100
```
- Operatori di confronto: `=`, `<`, `>`, `<=`, `>=`, `<>`
- Dopo THEN si possono mettere più istruzioni separate da `:`

### FOR...NEXT
Ciclo con contatore.

```
10 FOR I = 1 TO 10
20 PRINT I
30 NEXT I
```
- Opzioni: `STEP` per incremento diverso da 1
- `FOR I = 10 TO 1 STEP -1` conta alla rovescia

### GOSUB...RETURN
Chiamata a subroutine (come una funzione).

```
10 GOSUB 100
20 END
100 REM SUBROUTINE
110 PRINT "SOTTOPROGRAMMA"
120 RETURN
```
- `RETURN` torna all'istruzione dopo il `GOSUB`
- `END` termina il programma (evita di eseguire la subroutine per caduta)

### REM
Commento: tutto ciò che segue REM viene ignorato dall'interprete.

```
10 REM QUESTO E' UN COMMENTO
20 PRINT "OK" : REM ANCHE QUI
```

### POKE
Scrive un byte (0-255) in un indirizzo di memoria.

```
10 POKE 53280, 0  ' BORDO NERO
20 POKE 53281, 1  ' SFONDO BIANCO
30 POKE 646, 2    ' COLORE TESTO (ROSSO)
```

### PEEK
Legge un byte da un indirizzo di memoria.

```
10 X = PEEK(53280)
20 PRINT "COLORE BORDO:"; X
```

### SYS
Esegue codice macchina a un indirizzo specifico.

```
10 SYS 64738  ' RESET (equivalente a RUN/STOP + RESTORE)
```

### DATA / READ / RESTORE
Legge dati da una tabella nel programma.

```
10 DATA 1, 2, 3, "CIAO", 5
20 READ A
30 READ B$
40 PRINT A, B$
50 RESTORE
```
- `READ` legge il prossimo valore dalla lista DATA
- `RESTORE` riparte dall'inizio dei DATA

### DIM
Dimensiona un array.

```
10 DIM A(10)
20 FOR I = 0 TO 10
30 A(I) = I * 2
40 NEXT I
```
- Gli array partono da indice 0 per default
- Si possono usare `OPTION BASE 1` per far partire da 1

## Colori del C64

I registri colore principali:

| Indirizzo | Descrizione |
|-----------|-------------|
| 53280 | Colore bordo (0-15) |
| 53281 | Colore sfondo (0-16) |
| 646 | Colore testo corrente |

Tabella colori: 0=nero, 1=bianco, 2=rosso, 3=ciano, 4=viola, 5=verde, 6=blu, 7=giallo, 8=arancio, 9=marrone, 10=rosa, 11=grigio1, 12=grigio2, 13=verde chiaro, 14=blu chiaro, 15=grigio3

## Esempi completi

### Saluto personalizzato
```
10 INPUT "COME TI CHIAMI"; N$
20 PRINT "CIAO "; N$
30 INPUT "QUANTI ANNI HAI"; E
40 IF E < 18 THEN PRINT "GIOVANE!"
50 IF E >= 18 THEN PRINT "ADULTO!"
```

### Tabellina
```
10 INPUT "NUMERO"; N
20 FOR I = 1 TO 10
30 PRINT N; " X "; I; " = "; N * I
40 NEXT I
```

### Muovere un carattere sullo schermo
```
10 POKE 53280, 0: POKE 53281, 0
20 X = 10: Y = 10
30 POKE 1024 + X + Y * 40, 81
40 GET A$: IF A$ = "" THEN 40
50 POKE 1024 + X + Y * 40, 32
60 IF A$ = "D" THEN X = X + 1
70 IF A$ = "A" THEN X = X - 1
80 IF A$ = "W" THEN Y = Y - 1
90 IF A$ = "S" THEN Y = Y + 1
100 GOTO 30
```
(Si muove con WASD, 81 = codice carattere della lettera Q)

### Ciclo di colori
```
10 POKE 53280, 0
20 FOR C = 0 TO 15
30 POKE 53280, C
40 FOR T = 1 TO 500: NEXT T
50 NEXT C
60 GOTO 20
```

## Comandi non validi in BASIC V2

ATTENZIONE: questi comandi NON esistono in BASIC V2, sono di Assembly 6502:
- MOV, ADD, SUB, MUL, DIV (non esistono)
- JMP, CALL, ORG, DB, CINV (non esistono in BASIC)
- LDA, STA, LDX, ecc. (sono Assembly, non BASIC)

## Comandi di programmazione (non eseguibili da programma)
- `LIST`: elenca il programma in memoria
- `RUN`: esegue il programma
- `LOAD`: carica da nastro/disk drive
- `SAVE`: salva su nastro/disk drive
- `NEW`: cancella il programma corrente
- `CLR`: azzera le variabili

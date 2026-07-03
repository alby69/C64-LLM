---
title: "BASIC Language Vocabulary"
description: "Vocabolario completo dei comandi, istruzioni e funzioni BASIC del Commodore 64"
tags: [c64, basic, commands, reference, vocabulary]
source: "Commodore 64 Programmer's Reference Guide, Chapter 2"
---

# Capitolo 2: BASIC Language Vocabulary

## Introduzione

Il Commodore 64 BASIC (CBM BASIC) ha un vocabolario di 65 "keywords" con significati speciali. Questi keyword sono usati per costruire istruzioni di programma.

## Caratteristiche della tastiera C64

### Screen Editor
- Controlla l'output sullo schermo TV
- Gestisce l'editing del testo BASIC
- Intercetta input dalla tastiera

### Tasti speciali
- **RUN/STOP**: Interrompe l'esecuzione del programma
- **RESTORE**: In combinazione con RUN/STOP, resetta il computer
- **SHIFT + RUN/STOP**: Carica il primo file da cassette ed esegue (`LOAD"*",8` + `RUN`)

## Lista keyword BASIC

Ecco la lista completa dei 65 keyword BASIC del Commodore 64 in ordine alfabetico:

| Keyword | Abbreviazione | Tipo | Descrizione |
|---------|--------------|------|-------------|
| ABS | A | Funzione | Valore assoluto |
| AND | A | Operatore | AND logico |
| ASC | A | Funzione | Codice ASCII del primo carattere |
| ATN | A | Funzione | Arcotangente |
| CHR$ | C | Funzione | Carattere da codice ASCII |
| CLOSE | CL | Istruzione | Chiude file logico |
| CLR | C | Istruzione | Azzera variabili e array |
| CMD | C | Istruzione | Reindirizza output |
| CONT | C | Istruzione | Continua esecuzione dopo STOP |
| COS | C | Funzione | Coseno |
| DATA | D | Istruzione | Definisce dati per READ |
| DEF | D | Istruzione | Definisce funzione |
| DIM | D | Istruzione | Dichiara array |
| END | E | Istruzione | Termina programma |
| EXP | E | Funzione | Esponenziale (e^x) |
| FN | F | Funzione | Chiama funzione DEF |
| FOR | F | Istruzione | Inizio ciclo FOR...NEXT |
| FRE | F | Funzione | Byte di memoria liberi |
| GET | G | Istruzione | Legge un carattere dalla tastiera |
| GET# | G | Istruzione | Legge un carattere da file |
| GOSUB | GO | Istruzione | Salta a subroutine |
| GOTO | G | Istruzione | Salto incondizionato |
| IF | I | Istruzione | Condizionale |
| INPUT | I | Istruzione | Input da tastiera |
| INPUT# | I | Istruzione | Input da file |
| INT | I | Funzione | Parte intera |
| LEFT$ | LE | Funzione | Estrae caratteri da sinistra |
| LEN | L | Funzione | Lunghezza stringa |
| LET | L | Istruzione | Assegnazione (opzionale) |
| LIST | L | Comando | Elenca programma |
| LOAD | L | Comando | Carica programma |
| LOG | L | Funzione | Logaritmo naturale |
| MID$ | M | Funzione | Estrae caratteri dal centro |
| NEW | N | Comando | Cancella programma in memoria |
| NEXT | N | Istruzione | Fine ciclo FOR...NEXT |
| NOT | N | Operatore | NOT logico |
| ON | O | Istruzione | ON...GOTO / ON...GOSUB |
| OPEN | O | Istruzione | Apre file logico |
| OR | O | Operatore | OR logico |
| PEEK | P | Funzione | Legge valore da memoria |
| π (PI) | P | Costante | 3.141592654 |
| POKE | P | Istruzione | Scrive valore in memoria |
| POS | P | Funzione | Posizione cursore |
| PRINT | ? | Istruzione | Stampa output |
| PRINT# | P | Istruzione | Stampa su file |
| READ | R | Istruzione | Legge dati da DATA |
| REM | R | Istruzione | Commento |
| RESTORE | RE | Istruzione | Resetta puntatore DATA |
| RETURN | RE | Istruzione | Ritorna da GOSUB |
| RIGHT$ | R | Funzione | Estrae caratteri da destra |
| RND | R | Funzione | Numero casuale |
| RUN | R | Comando | Esegue programma |
| SAVE | S | Comando | Salva programma |
| SGN | S | Funzione | Segno del numero |
| SIN | S | Funzione | Seno |
| SPC | S | Funzione | Spazi nell'output |
| SQR | S | Funzione | Radice quadrata |
| STEP | ST | Istruzione | Incremento in FOR...NEXT |
| STOP | S | Istruzione | Arresta esecuzione |
| STR$ | ST | Funzione | Converte numero in stringa |
| SYS | S | Istruzione | Chiama routine macchina |
| TAB | T | Funzione | Tabulazione nell'output |
| TAN | T | Funzione | Tangente |
| THEN | T | Istruzione | Parte THEN di IF |
| TIME (TI) | T | Variabile | Timer interno (jiffies) |
| TIME$ (TI$) | T | Variabile | Timer interno (stringa) |
| TO | T | Istruzione | Usato in FOR...NEXT |
| USR | U | Funzione | Chiama funzione macchina |
| VAL | V | Funzione | Converte stringa in numero |
| VERIFY | V | Comando | Verifica programma salvato |
| WAIT | W | Istruzione | Attende cambiamento memoria |

## Tipi di keyword

### Comandi (Commands)
- Eseguibili solo in modalità DIRECT
- Non richiedono numero di linea
- Esempi: `NEW`, `LOAD`, `SAVE`, `RUN`, `LIST`, `VERIFY`

### Istruzioni (Statements)
- Usate nei programmi (con numeri di linea)
- Controllano il flusso del programma
- Esempi: `IF...THEN`, `FOR...NEXT`, `GOSUB...RETURN`, `POKE`, `PRINT`

### Funzioni (Functions)
- Restituiscono un valore
- Possono essere usate nelle espressioni
- Esempi: `ABS()`, `RND()`, `PEEK()`, `CHR$()`, `LEFT$()`

### Operatori (Operators)
- Modificano o combinano valori
- Esempi: `AND`, `OR`, `NOT`

## Screen Editor

L'editor schermo del C64 permette:
- Movimento cursore in tutte le direzioni
- Inserimento e cancellazione caratteri
- Colori e controllo cursore
- Editing di linee BASIC direttamente sullo schermo

### Tasti cursore
- **CRSR UP/DOWN**: Muove cursore su/giù
- **CRSR LEFT/RIGHT**: Muove cursore sinistra/destra
- **HOME**: Porta cursore in alto a sinistra
- **CLR/HOME**: Pulisce schermo e porta cursore home
- **INST/DEL**: Inserisce o cancella caratteri

---

*Per la descrizione dettagliata di ogni keyword, consultare la sezione "Description of BASIC Keywords" nel manuale originale (pagine 35-93).*

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

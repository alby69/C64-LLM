---
title: "BASIC Programming Rules"
description: "Regole fondamentali della programmazione BASIC per Commodore 64"
tags: [c64, basic, programming, fundamentals]
source: "Commodore 64 Programmer's Reference Guide, Chapter 1"
---

# Capitolo 1: BASIC Programming Rules

## Introduzione

Il sistema operativo del Commodore 64 è contenuto nei chip ROM ed è composto da tre moduli programma separati ma interrelati:

1. **BASIC Interpreter** - Analizza la sintassi BASIC ed esegue calcoli e manipolazione dati
2. **KERNAL** - Gestisce la maggior parte del processing a livello interrupt e l'I/O dati
3. **Screen Editor** - Controlla l'output sullo schermo e l'editing del testo BASIC

## Modalità di operazione BASIC

### DIRECT Mode
- Le istruzioni BASIC non hanno numeri di linea
- Vengono eseguite immediatamente quando si preme RETURN

### PROGRAM Mode
- Tutte le istruzioni BASIC devono avere numeri di linea
- Possono esserci più istruzioni per linea (separate da `:`)
- Limite di 80 caratteri per linea logica dello schermo
- **Nota importante**: Digitare sempre `NEW` prima di iniziare un nuovo programma

## Set di caratteri

Il Commodore 64 ha due set di caratteri completi:

### SET 1 (default)
- Maiuscole e numeri 0-9 disponibili senza SHIFT
- Tasti SHIFT + carattere = simboli grafici sul lato DESTRO dei tasti
- Tasti C= (Commodore) + carattere = simboli grafici sul lato SINISTRO dei tasti
- SHIFT + RUN/STOP = `LOAD"*",8` + `RUN`

### SET 2
- Minuscole e numeri 0-9 disponibili senza SHIFT
- Maiuscole con SHIFT
- Grafici con C= key

**Per cambiare set**: Premere `C=` + `SHIFT` contemporaneamente

## Caratteri speciali e loro uso

| Carattere | Nome | Descrizione |
|-----------|------|-------------|
| ` ` (spazio) | BLANK | Separa keywords e nomi variabili |
| `;` | SEMI-COLON | Usato nelle liste variabili per formattare output |
| `=` | EQUAL SIGN | Assegnazione valore e test relazionali |
| `+` | PLUS SIGN | Addizione aritmetica o concatenazione stringhe |
| `-` | MINUS SIGN | Sottrazione aritmetica, meno unario |
| `*` | ASTERISK | Moltiplicazione aritmetica |
| `/` | SLASH | Divisione aritmetica |
| `↑` | UP ARROW | Esponenziazione aritmetica |
| `(` `)` | PARENTHESES | Valutazione espressioni e funzioni |
| `%` | PERCENT | Dichiara variabile come intera |
| `#` | NUMBER | Precede il numero file logico nelle istruzioni I/O |
| `$` | DOLLAR SIGN | Dichiara variabile come stringa |
| `,` | COMMA | Formattazione output; separa parametri comandi |
| `.` | PERIOD | Punto decimale nei costanti floating-point |
| `"` | QUOTATION MARK | Racchiude costanti stringa |
| `:` | COLON | Separa istruzioni BASIC multiple in una linea |
| `?` | QUESTION MARK | Abbreviazione per il keyword PRINT |
| `<` | LESS THAN | Test relazionali |
| `>` | GREATER THAN | Test relazionali |
| `π` | PI | Costante numerica 3.141592654 |

## Costanti

### Numeri interi (Integer)
- Numeri senza punto decimale
- Range: **-32768 a +32767**
- Non usare virgole (es. 32000, non 32,000)
- Memorizzati in 2 byte

**Esempi**: `-12`, `8765`, `-32768`, `+44`, `0`

### Numeri floating-point
- Numeri positivi o negativi con frazioni
- Fino a 9 cifre visualizzate
- Range visualizzato: **-999999999 a +999999999**
- Memorizzati in 5 byte con 10 cifre di precisione
- Arrotondamento alla decima cifra

**Notazione scientifica**: `mantissa` + `E` + `esponente`
- E rappresenta ×10
- Range esponente: **-39 a +38**
- Numero massimo: **+1.70141183E+38** (?OVERFLOW ERROR se superato)
- Numero minimo: **+2.93873588E-39** (risultato 0 senza errore se inferiore)

**Esempi**:
- `235.988E-3` = 0.235988
- `2359E6` = 2359000000
- `-7.09E-12` = -0.00000000000709
- `-3.14159E+5` = -314159

### Stringhe
- Gruppi di informazioni alfanumeriche
- Lunghezza massima: fino allo spazio disponibile in una linea di 80 caratteri
- Possono contenere spazi, lettere, numeri, punteggiatura, caratteri di controllo colore/cursore
- **Non possono contenere virgolette doppie** (`"`)
- Stringa nulla = nessun carattere

**Esempi**: `"HELLO"`, `"$25,000.00"`, `"NUMBER OF EMPLOYEES"`

**Per includere virgolette in una stringa**: Usare `CHR$(34)`

## Variabili

### Tipi di variabili

| Tipo | Suffisso | Esempio | Valore default |
|------|----------|---------|----------------|
| Integer | `%` | `A%`, `CNT%` | 0 |
| Floating-point | (nessuno) | `A`, `FP` | 0 |
| String | `$` | `A$`, `NAME$` | "" (nulla) |

### Regole per i nomi variabili
- Lunghezza qualsiasi, ma **solo i primi 2 caratteri sono significativi**
- Primo carattere deve essere una lettera
- Non possono essere uguali a keyword BASIC
- Non possono contenere keyword al centro
- Caratteri ammessi: A-Z, 0-9

**Esempi validi**:
```basic
A$="GROSS SALES"
MTH$="JAN"+A$
K%=5
CNT%=CNT%+1
FP=12.5
SUM=FP*CNT%
```

## Array

- Tabelle di elementi dati associati referenziati da un singolo nome
- Tipi: integer, floating-point, string
- Dimensioni massime teoriche: 255
- Elementi per dimensione: fino a 32767
- Primo indice: **0**

### Calcolo memoria array
- 5 byte per nome array
- 2 byte per ogni dimensione
- 2 byte per elemento (integer) / 5 byte (floating-point) / 3 byte + caratteri (string)

### Esempi
```basic
A$(0)="GROSS SALES"
MTH$(K%)="JAN"
G2%(X)=5
CNT%(G2%(X))=CNT%(1)-2
FP(12*K%)=24.8
SUM(CNT%(1))=FP/K%
A(5)=0
B(5,6)=0
C(1,2,3)=0
```

## Espressioni e Operatori

### Espressioni aritmetiche

| Operatore | Operazione | Esempi |
|-----------|------------|--------|
| `+` | Addizione | `2+2`, `A+B+C` |
| `-` | Sottrazione | `4-1`, `A-B` |
| `*` | Moltiplicazione | `100*2`, `A*X1` |
| `/` | Divisione | `10/2`, `A/B` |
| `↑` | Esponenziazione | `2↑2` (=4), `3↑3` (=27) |

**Meno unario**: `-5`, `-9E4`, `-B`

### Operatori relazionali

| Operatore | Significato |
|-----------|-------------|
| `<` | Minore di |
| `=` | Uguale a |
| `>` | Maggiore di |
| `<=` | Minore o uguale |
| `>=` | Maggiore o uguale |
| `<>` | Diverso da |

- Risultato **vero = -1**, **falso = 0**
- Confronto stringhe carattere per carattere (sinistra a destra)

**Esempi**:
```basic
1=5-4      ' risultato: -1 (vero)
14>66      ' risultato: 0 (falso)
15>=15     ' risultato: -1 (vero)
```

### Operatori logici (Booleani)

| Operatore | Descrizione |
|-----------|-------------|
| `AND` | Risultato 1 solo se entrambi i bit sono 1 |
| `OR` | Risultato 1 se almeno un bit è 1 |
| `NOT` | Complemento logico di ogni bit |

**Tabella di verità**:
```
AND: 1 AND 1 = 1,  0 AND 1 = 0,  1 AND 0 = 0,  0 AND 0 = 0
OR:  1 OR 1 = 1,   0 OR 1 = 1,   1 OR 0 = 1,   0 OR 0 = 0
NOT: NOT 1 = 0,    NOT 0 = 1
XOR: 1 XOR 1 = 0,  1 XOR 0 = 1,  0 XOR 1 = 1,  0 XOR 0 = 0
```

**Esempi**:
```basic
IF A=100 AND B=100 THEN 10
A=96 AND 32: PRINT A    ' risultato: -97 (complemento a due)
IF A=100 OR B=100 THEN 20
A=64 OR 32: PRINT A     ' risultato: 96
IF NOT X=Y
```

## Gerarchia delle operazioni

1. Parentesi (più interne prima)
2. Esponenziazione (`↑`)
3. Negazione unaria (`-`)
4. Moltiplicazione e divisione (`*`, `/`)
5. Addizione e sottrazione (`+`, `-`)
6. Confronti relazionali (`<`, `=`, `>`, `<=`, `>=`, `<>`)
7. NOT logico
8. AND logico
9. OR logico

**Parentesi**: massimo 10 livelli di annidamento

## Operazioni sulle stringhe

L'unico operatore stringa è `+` (concatenazione):

```basic
10 A$="FILE": B$="NAME"
20 NAM$=A$+B$           ' risultato: "FILENAME"
30 RES$="NEW "+A$+B$    ' risultato: "NEW FILENAME"
```

## Tecniche di programmazione

### Conversioni dati
- Tutte le operazioni aritmetiche e relazionali usano floating-point
- Integer convertiti a floating-point per la valutazione
- Risultato convertito a integer se assegnato a variabile integer
- Conversione floating-point → integer: parte frazionaria **troncata**
- Se risultato fuori range ±32767: **?ILLEGAL QUANTITY ERROR**

### Uso dell'istruzione INPUT

```basic
10 PRINT "YOUR NAME": INPUT N$
20 PRINT "HELLO," N$
```

**Tipi di variabili con INPUT**:
```basic
10 PRINT "ENTER A NUMBER":INPUT A    ' numerica
20 PRINT "ENTER A WORD":INPUT A$     ' stringa
```

### Uso dell'istruzione GET

Il buffer tastiera contiene fino a 10 caratteri.

**Forma raccomandata**:
```basic
10 GET A$: IF A$="" THEN 10
```

**Esempio editor schermo**:
```basic
10 GET A$: IF A$="" THEN 10
100 PRINT A$;: GOTO 10
```

**Tasti funzione**:
```basic
20 IF A$=CHR$(133) THEN POKE 53280,8:GOTO 10   ' F1 - cambia colore bordo
30 IF A$=CHR$(134) THEN POKE 53281,4:GOTO 10   ' F3 - cambia colore sfondo
40 IF A$=CHR$(135) THEN A$="DEAR SIR:"+CHR$(13) ' F5 - inserisce testo
50 IF A$=CHR$(136) THEN A$="SINCERELY,"+CHR$(13) ' F7 - inserisce testo
```

## Come "crunchare" i programmi BASIC

Tecniche per ridurre la dimensione dei programmi:

1. **Abbreviare keyword** - Vedi Appendice A per la lista completa
2. **Usare numeri di linea corti** (1, 2, 3 invece di 100, 110, 120)
3. **Mettere istruzioni multiple per linea** (separate da `:`)
4. **Rimuovere istruzioni REM** quando il programma è completo
5. **Usare variabili** per numeri/parole usati ripetutamente
6. **Usare READ/DATA** per grandi quantità di dati
7. **Usare array/matrici** per liste di dati
8. **Eliminare spazi** (non necessari in BASIC)
9. **Usare GOSUB** per routine ripetute
10. **Usare TAB/SPC** invece di comandi cursore multipli

### Esempio prima/dopo crunching

**Prima**:
```basic
10 PRINT "HELLO.."
20 FOR T=1 TO 500: NEXT
30 PRINT "HELLO, AGAIN.."
40 GOTO 10
```

**Dopo**:
```basic
10 PRINT"HELLO..";:FORT=1TO500:NEXT:PRINT"HELLO,AGAIN..":GOTO10
```

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

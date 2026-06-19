---
title: "Programming Graphics on the Commodore 64"
description: "Guida completa alla programmazione grafica del Commodore 64: modalità carattere, bitmap, sprite e scrolling"
tags: [c64, graphics, sprites, bitmap, vic-ii, programming]
source: "Commodore 64 Programmer's Reference Guide, Chapter 3"
---

# Capitolo 3: Programming Graphics on the Commodore 64

## Panoramica grafica

Il Commodore 64 offre diverse modalità grafiche gestite dal chip **VIC-II (Video Interface Chip II)**:

### Modalità display carattere
- **Standard Character Mode** - 40×25 caratteri, 16 colori
- **Multi-Color Mode** - Caratteri a 4 colori
- **Extended Background Color Mode** - Fino a 4 colori di sfondo

### Modalità bitmap
- **Standard High-Resolution Bit Map Mode** - 320×200 pixel
- **Multi-Color Bit Map Mode** - 160×200 pixel, 4 colori per cella

### Sprite
- 8 sprite hardware indipendenti
- 24×21 pixel ciascuno
- Posizionamento indipendente sullo schermo
- Rilevamento collisione hardware

## Locazioni grafiche

### Video Bank Selection
Il VIC-II può accedere a 16KB di memoria alla volta (4 banchi):
- **Bank 0**: $0000-$3FFF (default)
- **Bank 1**: $4000-$7FFF
- **Bank 2**: $8000-$BFFF
- **Bank 3**: $C000-$FFFF

**Selezione banco**: Registro $DD00 (CIA #2 Port A)
```basic
POKE 56576, PEEK(56576) AND 252 + bank
```

### Screen Memory
- Indirizzo base: default $0400 (1024)
- 1000 byte (40×25)
- Contiene i codici carattere da visualizzare

### Color Memory
- Indirizzo: $D800 (55296) - $DBE7 (56295)
- 1000 byte (40×25)
- Contiene i colori per ogni posizione carattere

### Character Memory
- 256 caratteri definiti
- 8 byte per carattere (8×8 pixel)
- Default a $1000 (4096) in ROM
- Può essere ridefinito in RAM

## Standard Character Mode

### Definizioni carattere
- Ogni carattere = 8×8 pixel
- 1 bit per pixel (on/off)
- Colore carattere definito in Color Memory
- Colore sfondo definito dal registro background

### Caratteri programmabili
- Permettono di definire caratteri personalizzati
- Utile per giochi, icone, simboli speciali
- Si punta la VIC-II alla nuova tabella caratteri in RAM

## Multi-Color Mode Graphics

### Multi-Color Mode Bit
- Attivato impostando il bit 4 del registro controllo VIC-II ($D016)
- Caratteri a 4 colori (2 bit per pixel)
- Risoluzione orizzontale dimezzata: 4×8 pixel effettivi

### Colori disponibili in Multi-Color
1. Colore di sfondo (registro $D021)
2. Colore 1 (registro $D022)
3. Colore 2 (registro $D023)
4. Colore carattere (da Color Memory)

## Extended Background Color Mode

- Fino a 4 colori di sfondo diversi
- I bit alti del codice carattere selezionano il colore sfondo
- Colori sfondo: $D021, $D022, $D023, $D024

## Bit Mapped Graphics

### Standard High-Resolution Bit Map Mode
- Risoluzione: **320×200 pixel**
- 1 bit per pixel (on/off)
- 8000 byte per schermo
- Colore sfondo + colore primo piano per ogni blocco 8×8

#### Come funziona
1. La memoria bitmap contiene 1 bit per pixel
2. Ogni byte rappresenta 8 pixel orizzontali
3. 40 byte per riga (320 pixel / 8)
4. 25 righe × 40 byte = 1000 byte per schermo

### Multi-Color Bit Map Mode
- Risoluzione: **160×200 pixel**
- 2 bit per pixel = 4 colori per cella 4×8
- Colori definiti per ogni blocco 4×8

## Smooth Scrolling

- Scrolling hardware del VIC-II
- Registri X e Y offset ($D016 e $D011)
- Permette scrolling pixel-per-pixel
- Combinato con scrolling software per aree grandi

## Sprite

### Definire uno sprite
- Ogni sprite = 24×21 pixel
- 63 byte per sprite (3 byte × 21 righe)
- Memorizzati in memoria RAM

### Sprite Pointers
- 8 puntatori in Screen Memory ($07F8-$07FF)
- Ogni puntatore = blocco di 64 byte dove è definito lo sprite
- Formula: `puntatore = indirizzo_sprite / 64`

### Accendere uno sprite
```basic
POKE 53269, PEEK(53269) OR 2^N
```
Dove N è il numero dello sprite (0-7).

### Spegnere uno sprite
```basic
POKE 53269, PEEK(53269) AND (255 - 2^N)
```

### Colori sprite
- Registri $D027-$D02E (53287-53294)
- Un colore per sprite

### Multi-Color Mode per sprite
- Attivato per singolo sprite tramite registro $D01C
- 4 colori: trasparente, colore sprite, colore multi 1 ($D025), colore multi 2 ($D026)

### Sprite espansi
- Espansione X: registro $D01D (doppia larghezza)
- Espansione Y: registro $D017 (doppia altezza)

### Posizionamento sprite

#### Registri posizione
- X: $D000-$D00E (pari) - 53248-53262
- Y: $D001-$D00F (dispari) - 53249-53263

#### Coordinate
- X: 0-511 (9 bit, MSB in $D010)
- Y: 0-255
- Area visibile: X 24-343, Y 50-249

#### MSB per X
- Registro $D010 (53264)
- Bit N = 1 → coordinata X dello sprite N > 255

### Priorità display
- Sprite possono apparire davanti o dietro allo sfondo
- Registro $D01B (53275)
- Bit = 0: sprite davanti allo sfondo
- Bit = 1: sprite dietro allo sfondo

### Rilevamento collisioni

#### Sprite-to-Sprite
- Registro $D01E (53278) - lettura
- Bit N = 1: sprite N ha colliso con un altro sprite

#### Sprite-to-Background
- Registro $D01F (53279) - lettura
- Bit N = 1: sprite N ha colliso con lo sfondo

**Nota**: I registri collisione devono essere letti e poi azzerati (PEEK li azzera automaticamente).

## Altre caratteristiche grafiche

### Screen Blanking
- Spegnimento schermo per accesso CPU alla memoria video
- Registro $D011, bit 4

### Raster Register
- Registro $D012 - linea raster corrente
- Usato per effetti raster, split screen, cambio palette

### Interrupt Status Register
- Registro $D019 - stato interrupt VIC-II
- Usato per interrupt raster

### Combinazioni colore suggerite
- Vedi manuale originale per combinazioni ottimali

## Creare sprite in BASIC - Programma di esempio

```basic
10 PRINT "{CLR}SPRITE EXAMPLE"
20 V=53248:REM BASE VIC-II
30 FOR N=0 TO 62:POKE 832+N,0:NEXT:REM CLEAR SPRITE 0
40 POKE 832,255:POKE 833,129:POKE 834,129:POKE 835,129
50 POKE 836,129:POKE 837,129:POKE 838,255:REM DEFINE SHAPE
60 POKE 2040,13:REM SPRITE POINTER (832/64=13)
70 POKE V+39,1:REM SPRITE 0 COLOR (white)
80 POKE V+21,1:REM TURN ON SPRITE 0
90 POKE V+0,100:REM X POSITION
100 POKE V+1,100:REM Y POSITION
110 GET A$:IF A$="" THEN 110
120 POKE V+21,0:REM TURN OFF SPRITE
```

## Tabella riassuntiva registri VIC-II per sprite

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| $D000 | 53248 | Sprite 0 X |
| $D001 | 53249 | Sprite 0 Y |
| $D002 | 53250 | Sprite 1 X |
| $D003 | 53251 | Sprite 1 Y |
| ... | ... | ... |
| $D00E | 53262 | Sprite 7 X |
| $D00F | 53263 | Sprite 7 Y |
| $D010 | 53264 | MSB X coordinate |
| $D015 | 53269 | Sprite enable |
| $D017 | 53271 | Sprite Y expand |
| $D01B | 53275 | Sprite priority |
| $D01C | 53276 | Sprite multicolor |
| $D01D | 53277 | Sprite X expand |
| $D01E | 53278 | Sprite-sprite collision |
| $D01F | 53279 | Sprite-background collision |
| $D025 | 53285 | Sprite multicolor 1 |
| $D026 | 53286 | Sprite multicolor 2 |
| $D027 | 53287 | Sprite 0 color |
| $D028 | 53288 | Sprite 1 color |
| ... | ... | ... |
| $D02E | 53294 | Sprite 7 color |

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

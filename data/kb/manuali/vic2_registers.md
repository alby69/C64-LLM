# VIC-II Registers — Registri VIC-II ($D000-$D03F)

Il VIC-II (Video Interface Chip 2) è il chip grafico del Commodore 64. I suoi registri occupano lo spazio $D000-$D03F (64 byte, ma solo 47 usati).

## Memory Map VIC-II

| Indirizzo | Nome | Descrizione |
|-----------|------|-------------|
| $D000 | SP0X | Sprite 0 X position |
| $D001 | SP0Y | Sprite 0 Y position |
| $D002 | SP1X | Sprite 1 X position |
| $D003 | SP1Y | Sprite 1 Y position |
| $D004 | SP2X | Sprite 2 X position |
| $D005 | SP2Y | Sprite 2 Y position |
| $D006 | SP3X | Sprite 3 X position |
| $D007 | SP3Y | Sprite 3 Y position |
| $D008 | SP4X | Sprite 4 X position |
| $D009 | SP4Y | Sprite 4 Y position |
| $D00A | SP5X | Sprite 5 X position |
| $D00B | SP5Y | Sprite 5 Y position |
| $D00C | SP6X | Sprite 6 X position |
| $D00D | SP6Y | Sprite 6 Y position |
| $D00E | SP7X | Sprite 7 X position |
| $D00F | SP7Y | Sprite 7 Y position |
| $D010 | MSIGX | Sprite X position MSB (bit 9) |
| $D011 | SCROLY | Control register 1: scroll verticale, screen on/off, bitmap mode, extended color |
| $D012 | RASTER | Raster line compare (per raster interrupt) |
| $D013 | LPX | Light pen X |
| $D014 | LPY | Light pen Y |
| $D015 | SPENA | Sprite enable (1 bit per sprite) |
| $D016 | SCROLX | Control register 2: scroll orizzontale, multicolor mode |
| $D017 | SPSPCL | Sprite-sprite collision |
| $D018 | POINTER | Indirizzo base character set + screen RAM |
| $D019 | IRQF | Interrupt flag register |
| $D01A | IRQM | Interrupt mask register |
| $D01B | SPDBG | Sprite background priority |
| $D01C | SPMCOL | Sprite multicolor select |
| $D01D | SPXCOL | Sprite X expansion |
| $D01E | SPYCOL | Sprite Y expansion |
| $D01F | SPBGCL | Sprite-background collision |
| $D020 | BORDER | Border color |
| $D021 | BAKCOL | Background color 0 |
| $D022 | BAKCOL1 | Background color 1 |
| $D023 | BAKCOL2 | Background color 2 |
| $D024 | BAKCOL3 | Background color 3 |
| $D025 | SPMCOL0 | Sprite multicolor 0 |
| $D026 | SPMCOL1 | Sprite multicolor 1 |
| $D027 | SP0COL | Sprite 0 color |
| $D028 | SP1COL | Sprite 1 color |
| ... fino a $D02E | SP7COL | Sprite 7 color |
| $D02F | COLOR | Sempre uguale a $D020 (border) |
| $D030 | — | Non usato |

## Registri di Controllo

### $D011 — SCROLY (Control Register 1)

```
Bit 7:  Raster line MSB (9° bit di $D012)
Bit 6:  Extended color mode
Bit 5:  Bitmap mode
Bit 4:  Screen on/off (1=on, 0=off. Quando spento si vede solo il bordo)
Bit 3-0: Scroll verticale (0-7 pixel)
```

### $D016 — SCROLX (Control Register 2)

```
Bit 7:  Reset per raster interrupt (non usato normalmente)
Bit 6:  Multicolor mode
Bit 5:  Screen on/off (alternativo, normalmente a 1)
Bit 4:  — (non usato)
Bit 3-0: Scroll orizzontale (0-7 pixel)
```

### $D018 — POINTER (Memory Pointer)

```
Bit 7-4: Indirizzo base Character Set / Bitmap (incrementi di $0400)
          0000 = $0000, 0001 = $0400, ..., 1111 = $F000
Bit 3-0: Indirizzo base Screen RAM (incrementi di $0400)
          0000 = $0000, 0001 = $0400, ..., 1111 = $F000
```

Configurazione tipica: `LDA #$18` → character set = $3000, screen = $0400

### $D019 — IRQF (Interrupt Flag)

```
Bit 7:  Any interrupt occurred
Bit 3:  Light pen
Bit 2:  Sprite-sprite collision
Bit 1:  Sprite-background collision
Bit 0:  Raster compare
```

### $D01A — IRQM (Interrupt Mask)

Stessi bit di $D019. Per abilitare un interrupt: setta il bit corrispondente.

## Esempi Base

### Cambiare colore bordo e sfondo
```
      LDA #$00       ; nero
      STA $D020      ; bordo nero
      STA $D021      ; sfondo nero
```

### Abilitare schermo bitmap
```
      LDA #$3B       ; %00111011 = bitmap mode + screen on
      STA $D011
```

### Leggere la riga raster corrente
```
      LDA $D012      ; raster line low byte (0-255)
      LDX $D011      ; per il bit 7 (MSB)
      AND #$80       ; isola il bit 7
      STA MSB        ; salva MSB
```

## VIC-II Memory Access (Bad Lines)

Il VIC-II ha accesso prioritario alla memoria e può "rubare" cicli alla CPU. Durante una "bad line", la CPU viene fermata per 40-43 cicli mentre il VIC-II legge 40 byte di character data. Le bad line avvengono quando:
- $D011 bit 4 = 1 (screen on)
- $D016 bit 5 = 1 (screen on alternativo)
- Riga corrente mod 8 == Y scroll

Questo è fondamentale per effetti come raster split e scrolling liscio.

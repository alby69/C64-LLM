# Sprite Programming — Programmazione degli Sprite sul C64

Il VIC-II supporta 8 sprite hardware, ciascuno 24x21 pixel. Possono essere in alta risoluzione (1 colore + trasparente) o multicolor (3 colori + trasparente).

## Memoria degli Sprite

### Definizione dello Sprite (Pixel Data)

Ogni sprite occupa 64 byte:
- 24 pixel/riga × 21 righe = 504 bit = 63 byte + 1 byte non usato
- Byte 0-2: riga 0 (3 byte = 24 pixel)
- Byte 3-5: riga 1
- ... fino a byte 60-62: riga 20

### Indirizzamento

Il puntatore dello sprite è un byte nella "sprite pointer area", che occupa gli ultimi 8 byte di ogni blocco da 1KB della Screen RAM.

Con screen RAM a $0400 (default):
```
$07F8 = puntatore sprite 0
$07F9 = puntatore sprite 1
...
$07FF = puntatore sprite 7
```

Valore del puntatore: indirizzo / $40 (cioè numero di blocco da 64 byte). Quindi:
- Valore 128 ($80) → sprite a $2000
- Valore 192 ($C0) → sprite a $3000
- Valore 13 → sprite a $0340

## Registri degli Sprite

### Posizione
```
$D000-$D00F: X/Y position per sprite 0-7
$D010:       MSB X (bit 0-7 per sprite 0-7, X a 9 bit)
```

### Attributi
```
$D015: Sprite enable       (1 bit per sprite)
$D017: Sprite Y expand     (1=doppia altezza)
$D01B: Sprite priority     (1=dietro sfondo, 0=primo piano)
$D01C: Multicolor select    (1=multicolor)
$D01D: Sprite X expand     (1=doppia larghezza)
$D01E: Sprite Y expand     (espansione verticale)
```

### Colori
```
$D027-$D02E: Colore sprite 0-7 (alta risoluzione)
$D025: Sprite multicolor 0 (colore condiviso)
$D026: Sprite multicolor 1 (colore condiviso)
```

### Collisioni
```
$D019 bit 2: Sprite-sprite collision flag
$D019 bit 1: Sprite-background collision flag
$D01F: Sprite-sprite collision register (quali sprite)
$D01E: Sprite-background collision register
```

## Esempio: Muovere uno Sprite

```
; Abilita sprite 0
      lda #$01
      sta $D015

; Imposta colore sprite 0
      lda #$0A       ; rosso chiaro
      sta $D027

; Posizione sprite 0 a (100, 150)
      lda #100
      sta $D000      ; X low
      lda #150
      sta $D001      ; Y
      lda #$00
      sta $D010      ; MSB X (bit 0)

; Puntatore sprite 0 = $0340 / $40 = $0D = 13
      lda #13
      sta $07F8
```

## Esempio: Sprite in Movimento (Animazione)

```
loop:
      inc $D000      ; sprite 0 X +1
      lda $D000
      cmp #$80       ; se X > 128, inverti direzione
      bne loop
      dec $D000
      jmp loop

; Per movimento fluido: sincronizzare col raster
wait:
      lda $D012
      cmp #$FF       ; aspetta riga 255
      bne wait
      inc $D000
      jmp wait
```

## Sprite Multicolor

In modalità multicolor ogni pixel è 2 bit:
```
%00 = trasparente
%01 = colore sprite ($D027-$D02E)
%10 = sprite multicolor 0 ($D025)
%11 = sprite multicolor 1 ($D026)
```

```
; Imposta sprite 0 in multicolor
      lda #$01
      sta $D01C      ; sprite 0 multicolor
      lda #$07       ; colore condiviso 0 = giallo
      sta $D025
      lda #$02       ; colore condiviso 1 = rosso
      sta $D026
      lda #$0F       ; colore sprite 0 = grigio
      sta $D027
```

Lo sprite multicolor è 12 pixel di larghezza (24 pixel in alta risoluzione, ogni byte codifica 4 pixel invece di 8).

## Espansione Sprite

```
; Raddoppia larghezza sprite 0
      lda #$01
      sta $D01D

; Raddoppia altezza sprite 0
      lda #$01
      sta $D017
```

## Sprite Collision Detection

```
; Leggi collisioni sprite-sprite
      lda $D01F      ; bit 0-7 = sprite 0-7 che collidono
      and #$01       ; sprite 0 collide?
      bne collision

; Leggi collisioni sprite-sfondo
      lda $D01E
      and #$01       ; sprite 0 collide con sfondo?
      bne hit

; Pulisci flag (leggi $D019)
      lda $D019
      and #$04       ; sprite-sprite collision?
      beq no_collision
      lda $D01F      ; leggi per azzerare automaticamente
```

## Note Importanti

- **Sprite pointer va ricaricato** ogni volta che si cambia la definizione dello sprite.
- **Expansione X/Y** raddoppia i pixel senza cambiare i dati dello sprite.
- **Sprite priority** ($D01B): se il bit è 1, lo sprite appare DIETRO i caratteri dello schermo (utile per maschere/effetti).
- **Sprite-sprite collision** (§D01F) e **sprite-background** (§D01E) vanno letti subito dopo che si verifica la collisione, altrimenti vengono azzerati.
- **Limite di 8 sprite per riga** — se ne hai di più sulla stessa riga, scompaiono.

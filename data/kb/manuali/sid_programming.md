# SID Sound Programming — Programmazione del SID ($D400-$D418)

Il SID (Sound Interface Device) 6581/8580 è il chip audio del Commodore 64. Tre voci indipendenti, ciascuna con oscillatore, inviluppo e filtro programmabili.

## Memory Map SID

| Indirizzo | Voce | Descrizione |
|-----------|------|-------------|
| $D400 | 1 | Frequency low byte (frequenza oscillatore) |
| $D401 | 1 | Frequency high byte |
| $D402 | 1 | Pulse width low byte (larghezza impulso PWM) |
| $D403 | 1 | Pulse width high byte |
| $D404 | 1 | Control register: forma d'onda + gate |
| $D405 | 1 | Attack/Decay (ADSR envelope) |
| $D406 | 1 | Sustain/Release (ADSR envelope) |
| $D407 | 2 | Frequency low byte |
| $D408 | 2 | Frequency high byte |
| $D409 | 2 | Pulse width low byte |
| $D40A | 2 | Pulse width high byte |
| $D40B | 2 | Control register |
| $D40C | 2 | Attack/Decay |
| $D40D | 2 | Sustain/Release |
| $D40E | 3 | Frequency low byte |
| $D40F | 3 | Frequency high byte |
| $D410 | 3 | Pulse width low byte |
| $D411 | 3 | Pulse width high byte |
| $D412 | 3 | Control register |
| $D413 | 3 | Attack/Decay |
| $D414 | 3 | Sustain/Release |
| $D415 | — | Cutoff filter low (filtro passa-basso) |
| $D416 | — | Cutoff filter high / resonance |
| $D417 | — | Filtro: route voce + modalità filtro |
| $D418 | — | Volume + filtri abilitati |

## Control Register ($D404, $D40B, $D412)

```
Bit 7:  Noise (rumore bianco)
Bit 6:  — (non usato)
Bit 5:  Pulse (onda quadra PWM)
Bit 4:  Sawtooth (onda a dente di sega)
Bit 3:  Triangle (onda triangolare)
Bit 2:  Test (azzera oscillatore, utile per sincronizzazione)
Bit 1:  Ring modulation (modulazione ad anello con voce precedente)
Bit 0:  Gate (1=attacca inviluppo, 0=rilascia)
```

Una sola forma d'onda per volta: bit 3 XOR 4 XOR 5 XOR 7.

## ADSR Envelope ($D405/$D406)

```
$D405 (Attack/Decay):
  Bit 7-4: Attack (0-15, velocità di attacco)
  Bit 3-0: Decay  (0-15, velocità di decadimento)

$D406 (Sustain/Release):
  Bit 7-4: Sustain (0-15, volume sostenuto)
  Bit 3-0: Release (0-15, velocità di rilascio)
```

Valori: 0 = più veloce, 15 = più lento. Tempi reali da 2ms a 8s.

## Filter Register ($D415-$D418)

```
$D415: Cutoff filter low byte (11 bit totali)
$D416: Bit 7-4: Resonance (0-15)
       Bit 3-0: Cutoff filter high byte (bits 8-10)

$D417: Route filtro per voce:
  Bit 7:  Voice 3 off (voice 3 non passa dal filtro)
  Bit 6:  Voice 2 off
  Bit 5:  Voice 1 off
  Bit 4:  Voice 3 on (voice 3 passa dal filtro)
  Bit 3:  Voice 2 on
  Bit 2:  Voice 1 on
  Bit 1:  High pass filter
  Bit 0:  Band pass filter
  (Low pass filter = nessun bit o entrambi? No: low pass = bit 0 e 1 a 0)

$D418:
  Bit 7:  Filter on/off (1=filtro attivo sul volume)
  Bit 6-4: Volume (0-15)
  Bit 3:  — (non usato)
  Bit 0-2: — (non usato)
```

## Esempio: Suonare una Nota (Voce 1)

```
; Frequenza = LA4 (440 Hz)
      lda #<$D400_freq(440)
      sta $D400
      lda #>$D400_freq(440)
      sta $D401

; Onda quadra con pulse 50%
      lda #$00
      sta $D402      ; pulse low
      lda #$08
      sta $D403      ; pulse high (50% = $0800 su $1000)

; ADSR: attack 2, decay 4, sustain 12, release 8
      lda #$24       ; attack=2, decay=4
      sta $D405
      lda #$C8       ; sustain=12, release=8
      sta $D406

; Accendi la nota: gate + pulsre waveform
      lda #$11       ; bit 4 (pulse) + bit 0 (gate)
      sta $D404

; Aspetta un po'
      ldx #100
delay:
      dex
      bne delay

; Spegni: solo gate off
      lda #$10       ; solo pulse, gate=0
      sta $D404
```

## Calcolo Frequenza

La frequenza del SID si calcola:
```
freq = (nota_Hz × $D400_clock) / $1000000
```
Dove il clock SID è ~985248 Hz (PAL) o ~1022727 Hz (NTSC).

Per 440 Hz su PAL:
```
freq = (440 × 985248) / 1048576 = 413
$D400_lo = $9D  (413 & $FF)
$D400_hi = $01  (413 >> 8)
```

## Tabella Note (Valori per PAL)

| Nota | Ottava 0 | Ottava 1 | Ottava 2 | Ottava 3 | Ottava 4 |
|------|----------|----------|----------|----------|----------|
| C    | $0048 | $0091 | $0122 | $0244 | $0488 |
| C#   | $004C | $009A | $0134 | $0268 | $04D0 |
| D    | $0051 | $00A3 | $0147 | $028E | $051C |
| D#   | $0056 | $00AD | $015B | $02B6 | $056C |
| E    | $005C | $00B8 | $0170 | $02E0 | $05C0 |
| F    | $0062 | $00C4 | $0188 | $0310 | $0620 |
| F#   | $0068 | $00D0 | $01A1 | $0342 | $0684 |
| G    | $006F | $00DE | $01BC | $0378 | $06F0 |
| G#   | $0076 | $00EC | $01D8 | $03B0 | $0760 |
| A    | $007D | $00FB | $01F6 | $03EC | $07D8 |
| A#   | $0084 | $010A | $0214 | $0428 | $0850 |
| B    | $008C | $0119 | $0232 | $0464 | $08C8 |

## Effetto Sirena (Frequenza Variabile)

```
siren:
      ldx #0
up:
      stx $D400      ; sweep frequenza verso l'alto
      dex
      cpx #$FF
      bne up
down:
      stx $D400      ; sweep verso il basso
      inx
      bne down
      jmp siren
```

## Noise per Effetti Percussivi

```
; Suono di rullante (snare)
      lda #$C1       ; noise + gate, attack veloce
      sta $D404
      lda #$80       ; attack=8, decay=0
      sta $D405
      lda #$01       ; sustain=0, release=1
      sta $D406
      ldx #10
      dex
      bne *-1
      lda #$C0       ; gate off
      sta $D404
```

## Note Importanti

- **SID 6581 (old)** e **8580 (new)** hanno suoni diversi: il 8580 è più pulito, il 6581 più distorto.
- **Ring modulation** (bit 1 del control register) funziona solo se la voce precedente ha triangle wave.
- **Test bit** (bit 2) azzera l'oscillatore. Utile per sincronizzare due voci (sincronizzazione hard).
- **Volume ($D418)**: bit 6-4. Volume 0 = silenzio. Non dimenticare di impostarlo!
- **Filtro**: se $D418 bit 7 = 1, passa tutto dal filtro. Le voci non filtrate ($D417 bit 7=1, bit 6=1, bit 5=1) saranno silenziose.

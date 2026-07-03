---
title: "Programming Sound and Music on the Commodore 64"
description: "Guida completa alla programmazione audio del Commodore 64 con il chip SID 6581"
tags: [c64, sound, music, sid, audio, synthesis]
source: "Commodore 64 Programmer's Reference Guide, Chapter 4"
---

# Capitolo 4: Programming Sound and Music on Your Commodore 64

## Introduzione

Il Commodore 64 è equipaggiato con il chip audio **SID (Sound Interface Device) 6581**, il sintetizzatore integrato più sofisticato disponibile su qualsiasi computer personale.

### Caratteristiche del SID
- **3 voci completamente programmabili**
- **9 ottave musicali complete**
- **4 forme d'onda controllabili**
- Filtri programmabili
- Generatore di inviluppo (ADSR)
- Ring modulation e synchronization

## Controllo volume

Il volume master è controllato dal registro $D418 (54296):
```basic
POKE 54296, 15   ' Volume massimo
POKE 54296, 0    ' Muto
```

Valori: 0-15

## Frequenze delle onde sonore

Ogni voce ha un registro frequenza a 16 bit:
- Voce 1: $D400-$D401 (54272-54273)
- Voce 2: $D407-$D408 (54279-54280)
- Voce 3: $D40E-$D40F (54286-54287)

Formula: `FREQUENCY = (REGISTER_VALUE * CLOCK) / 16777216`
Dove CLOCK = 1.023 MHz (PAL) o 1.02273 MHz (NTSC)

## Uso di voci multiple

### Registri per voce

Ogni voce ha questi registri:

| Registro | Indirizzo | Funzione |
|----------|-----------|----------|
| Frequency Low | $D400/$D407/$D40E | Byte basso frequenza |
| Frequency High | $D401/$D408/$D40F | Byte alto frequenza |
| Pulse Width Low | $D402/$D409/$D410 | Larghezza impulso (basso) |
| Pulse Width High | $D403/$D40A/$D411 | Larghezza impulso (alto) |
| Control | $D404/$D40B/$D412 | Registro controllo |
| Attack/Decay | $D405/$D40C/$D413 | Tempo attack e decay |
|Sustain/Release | $D406/$D40D/$D414 | Livello sustain e release |

### Registro controllo voce ($D404, $D40B, $D412)

| Bit | Funzione |
|-----|----------|
| 0 | Gate (1=on, 0=off) |
| 1 | Sync (sincronizza con voce precedente) |
| 2 | Ring Mod (modulazione ad anello) |
| 3 | Test |
| 4 | Triangle wave |
| 5 | Sawtooth wave |
| 6 | Pulse wave |
| 7 | Noise |

**Nota**: Solo una forma d'onda alla volta per voce (tranne noise che non si combina).

### Controllo voci multiple

```basic
10 V=54296:F1=54272:C1=54276:AD1=54277:SR1=54278
20 POKE V,15:REM VOLUME MAX
30 POKE F1,0:POKE F1+1,0:REM FREQUENCY VOCE 1
40 POKE C1,17:REM TRIANGLE + GATE ON
50 POKE AD1,0:POKE SR1,240:REM ATTACK=0, DECAY=0, SUSTAIN=15, RELEASE=0
```

## Cambiare forme d'onda

### Forme d'onda disponibili

1. **Triangle (Triangolare)** - Bit 4 = 1
   - Suono morbido, simile flauto
   - Valore registro: 16 + gate

2. **Sawtooth (Dente di sega)** - Bit 5 = 1
   - Suono ricco, simile violino
   - Valore registro: 32 + gate

3. **Pulse (Impulso/Quadra)** - Bit 6 = 1
   - Suono cavo, simile clarinetto
   - Richiede impostazione Pulse Width
   - Valore registro: 64 + gate

4. **Noise (Rumore)** - Bit 7 = 1
   - Suono percussivo, effetti speciali
   - Valore registro: 128 + gate

### Esempio cambio forma d'onda

```basic
10 V=54296:F=54272:C=54276
20 POKE V,15
30 FOR W=16 TO 128 STEP 32
40 POKE F,0:POKE F+1,50
50 POKE C,W+1:REM GATE ON CON FORMA D'ONDA
60 FOR T=1 TO 500:NEXT
70 POKE C,W:REM GATE OFF
80 FOR T=1 TO 200:NEXT
90 NEXT W
```

## Generatore di inviluppo (ADSR)

L'inviluppo controlla come evolve il volume di una nota nel tempo:

### Fasi ADSR

```
Volume
  |
  |     /\___
  |    /  \   \
  |   /    \   \
  |  /      \___\
  |_/        A  D S  R
  +--------------------> Tempo
   A=Attack D=Decay S=Sustain R=Release
```

### Registri ADSR

**Attack/Decay** ($D405, $D40C, $D413):
- Nibble alto (4 bit alti): Attack (0-15)
- Nibble basso (4 bit bassi): Decay (0-15)

**Sustain/Release** ($D406, $D40D, $D414):
- Nibble alto: Sustain level (0-15)
- Nibble basso: Release (0-15)

### Valori Attack/Decay/Release

| Valore | Tempo |
|--------|-------|
| 0 | 2 ms |
| 1 | 8 ms |
| 2 | 16 ms |
| 3 | 24 ms |
| 4 | 38 ms |
| 5 | 56 ms |
| 6 | 68 ms |
| 7 | 80 ms |
| 8 | 100 ms |
| 9 | 250 ms |
| 10 | 500 ms |
| 11 | 800 ms |
| 12 | 1 s |
| 13 | 3 s |
| 14 | 5 s |
| 15 | 8 s |

### Esempio ADSR

```basic
10 V=54296:F=54272:C=54276:AD=54277:SR=54278
20 POKE V,15
30 POKE F,0:POKE F+1,50
40 POKE AD,22:REM ATTACK=1, DECAY=6
50 POKE SR,97:REM SUSTAIN=6, RELEASE=1
60 POKE C,33:REM SAWTOOTH + GATE ON
70 FOR T=1 TO 1000:NEXT
80 POKE C,32:REM GATE OFF (inizia release)
```

## Filtri

Il SID include un filtro programmabile:

### Registro filtro cutoff ($D415-$D416)
- 11 bit di risoluzione
- Frequenza di cutoff: 30 Hz - 12 kHz

### Registro controllo filtro ($D417)
| Bit | Funzione |
|-----|----------|
| 0 | Filtro voce 1 |
| 1 | Filtro voce 2 |
| 2 | Filtro voce 3 |
| 3 | Filtro voce esterna |
| 4 | Modalità Low-pass |
| 5 | Modalità Band-pass |
| 6 | Modalità High-pass |

### Registro volume/filtro ($D418)
| Bit | Funzione |
|-----|----------|
| 0-3 | Volume master |
| 4 | Filtro on/off |
| 7 | Voce 3 off (usare come modulatore) |

### Esempio filtro

```basic
10 V=54296:FC=54295:FF=54294:FR=54293
20 POKE V,15+16:REM VOLUME + FILTRO ON
30 POKE FF,255:POKE FC,7:REM CUTOFF ALTO
40 POKE FR,21:REM LOW-PASS, VOCE 1 FILTRATA
```

## Tecniche avanzate

### Effetti speciali
- **Drum sounds**: Combinazione noise + ADSR rapido
- **Arpeggi**: Cambio rapido frequenza
- **Vibrato**: Modulazione frequenza con voce 3
- **Portamento**: Scivolamento tra note

### Sincronizzazione e Ring Modulation

**Sync** (Bit 1 del registro controllo):
- Sincronizza la frequenza di una voce con quella precedente
- Voce 2 sync con voce 1, voce 3 sync con voce 2

**Ring Mod** (Bit 2 del registro controllo):
- Modulazione ad anello tra voci
- Crea timbri complessi

### Esempio ring modulation

```basic
10 V=54296:F1=54272:C1=54276:F2=54279:C2=54283
20 POKE V,15
30 POKE F1,0:POKE F1+1,100:REM FREQUENCY VOCE 1
40 POKE F2,0:POKE F2+1,50:REM FREQUENCY VOCE 2
50 POKE C1,21:REM TRIANGLE + RING MOD + GATE
60 POKE C2,16:REM TRIANGLE (carrier)
```

## Tabella note musicali

Vedi Appendice E per i valori di frequenza completi per tutte le note.

### Esempio scala

```basic
10 V=54296:F=54272:C=54276
20 POKE V,15
30 FOR N=0 TO 11
40 READ FL,FH
50 POKE F,FL:POKE F+1,FH
60 POKE C,33:REM SAWTOOTH + GATE ON
70 FOR T=1 TO 200:NEXT
80 POKE C,32:REM GATE OFF
90 FOR T=1 TO 50:NEXT
100 NEXT N
110 DATA 143,34,170,36,198,38,234,40,22,43,63,45
120 DATA 111,48,170,51,239,54,63,58,154,62,1,66
```

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

---
title: "Input/Output Guide"
description: "Guida completa alle periferiche e porte di input/output del Commodore 64"
tags: [c64, io, serial-bus, rs232, user-port, game-port, printer, disk, cassette]
source: "Commodore 64 Programmer's Reference Guide, Chapter 6"
---

# Capitolo 6: Input/Output Guide

## Introduzione

Il Commodore 64 offre molteplici interfacce per comunicare con dispositivi esterni:
- Output TV (video composito)
- Porta seriale (per floppy disk, stampanti)
- Porta cassette (Datassette)
- Porta RS-232 (modem, terminali)
- Porta utente (User Port)
- Porte giochi (Game Ports)
- Porta espansione (Expansion Port)

## Output alla TV

Il C64 può essere collegato a:
- **TV via antenna** (modulatore RF)
- **Monitor via video composito**
- **Monitor S-Video**

### Colori disponibili
16 colori: nero, bianco, rosso, ciano, viola, verde, blu, giallo, arancione, marrone, rosa chiaro, grigio scuro, grigio medio, verde chiaro, azzurro chiaro, grigio chiaro.

## Output ad altri dispositivi

### Output alla stampante

#### Comandi BASIC
```basic
OPEN 1,4       ' Apre canale alla stampante (device 4)
CMD 1          ' Reindirizza output alla stampante
PRINT "HELLO"  ' Stampa sulla stampante
PRINT#1,"TEXT" ' Stampa direttamente su file logico 1
CLOSE 1        ' Chiude canale
```

#### Device numbers comuni
- Device 4: Stampante
- Device 5: Stampante con formato plotter

### Output al modem

#### Comandi BASIC
```basic
OPEN 2,2,0,"300"  ' Apre RS-232 a 300 baud
PRINT#2,"ATDT"    ' Invia comando modem
```

## Lavorare con il nastro (Cassette Tape)

### Comandi BASIC
```basic
SAVE "NOMEPROGRAMMA"    ' Salva su nastro
LOAD "NOMEPROGRAMMA"    ' Carica da nastro
VERIFY "NOMEPROGRAMMA"  ' Verifica programma salvato
```

### Device number
- Device 1: Datassette

### Note
- Il C64 usa il formato Commodore (non standard Kansas City)
- Velocità: circa 300 baud
- Il pulsante PLAY deve essere premuto prima del comando LOAD/SAVE

## Archiviazione dati su floppy disk

### Comandi BASIC
```basic
SAVE "NOME",8      ' Salva su disco (device 8)
LOAD "NOME",8      ' Carica da disco
VERIFY "NOME",8    ' Verifica
OPEN 15,8,15       ' Apre canale comandi
PRINT#15,"I"       ' Inizializza disco
PRINT#15,"N:DISKNAME,ID" ' Formatta nuovo disco
CLOSE 15
```

### Device numbers
- Device 8: Primo floppy disk (1541)
- Device 9: Secondo floppy disk
- Device 10-11: Dischi aggiuntivi

### Comandi disco (canale 15)
```
N: nome,id    - Formatta nuovo disco
I             - Inizializza
V             - Verifica disco
S:nome        - Scratch (cancella) file
R:new=old     - Rinomina file
C:new=old     - Copia file
```

## Le porte giochi (Game Ports)

Il C64 ha due porte joystick/paddle sul retro.

### Paddle
- Due paddle per porta (4 totali)
- Resistenza variabile 0-470K ohm
- Lettura tramite SID ($D419-$D41A)
- Pulsante fire: bit 4/5 di $DC00/$DC01

### Penna ottica (Light Pen)
- Connessa alla porta joystick
- Coordinate lette dai registri VIC-II ($D013-$D014)
- Trigger: bit 4 di $DC00

## Interfaccia RS-232

### Descrizione generale
- Velocità: 50-2400 baud
- Formati: 5-8 bit dati, 1-2 bit stop, parità opzionale
- Connessione: User Port con adattatore

### Aprire un canale RS-232
```basic
OPEN 2,2,0,"300"   ' 300 baud, default settings
OPEN 2,2,0,"1200,0" ' 1200 baud, formato specifico
```

### Formato stringa RS-232
```
"baud,format"
```
- baud: 50, 75, 110, 134.5, 150, 300, 600, 1200, 1800, 2400
- format: codice per bit dati, parità, stop bit

### Ricevere dati da RS-232
```basic
OPEN 2,2,0,"300"
GET#2,A$
```

### Inviare dati a RS-232
```basic
OPEN 2,2,0,"300"
PRINT#2,"TESTO"
```

### Chiudere canale RS-232
```basic
CLOSE 2
```

### Puntatori buffer RS-232
- Base input buffer: $F7-$F8 (247-248)
- Base output buffer: $F9-$FA (249-250)

## La porta utente (User Port)

### Descrizione pin

| Pin | Funzione |
|-----|----------|
| 1 | GND |
| 2 | +5V (100mA max) |
| 3 | RESET |
| 4 | CNT1 (Timer A CIA #2) |
| 5 | SP1 (Serial port CIA #2) |
| 6 | CNT2 (Timer B CIA #2) |
| 7 | SP2 |
| 8 | PC2 (Handshaking) |
| 9 | ATN (Serial bus) |
| 10 | +9V AC |
| 11 | 9V AC |
| 12 | GND |

### Porte dati
- Port B CIA #2: $DD01 (56577)
- Data direction: $DD03 (56579)

### Esempio output User Port
```basic
POKE 56579,255    ' Imposta tutti i pin come output
POKE 56577,170    ' Output pattern 10101010
```

## Il bus seriale (Serial Bus)

### Descrizione
- Bus seriale Commodore per collegare periferiche
- Fino a 8 dispositivi sulla stessa linea
- Protocollo proprietario Commodore

### Pinout bus seriale

| Pin | Segnale | Descrizione |
|-----|---------|-------------|
| 1 | SRQ | Serial SRQ IN |
| 2 | GND | Ground |
| 3 | ATN | Attention |
| 4 | CLK | Serial Clock IN/OUT |
| 5 | DATA | Serial Data IN/OUT |
| 6 | RESET | Reset |

### Comandi bus seriale
- LISTEN: Il computer ascolta un dispositivo
- TALK: Il dispositivo parla al computer
- UNTALK/UNLISTEN: Fine comunicazione
- SECOND: Invia indirizzo secondario

## La porta espansione (Expansion Port)

### Caratteristiche
- Consente di espandere le capacità del C64
- Supporta cartridge ROM/RAM
- Accesso diretto al bus di sistema
- Slot per Z-80 CP/M cartridge

### Cartridge
- 8K o 16K ROM cartridge
- Si inseriscono nella porta espansione
- Possono contenere giochi, linguaggi, utility

## Cartridge Z-80 Microprocessore

### Commodore CP/M
- Sistema operativo CP/M per C64
- Richiede cartridge Z-80
- Accesso a vasta libreria software CP/M

### Avviare CP/M
1. Inserire cartridge Z-80
2. Accendere o resettare il computer
3. Il sistema carica CP/M automaticamente

---

*Fonte: Commodore 64 Programmer's Reference Guide, First Edition, Eighth Printing 1983*

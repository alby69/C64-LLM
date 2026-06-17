---
title: "CIA Chips — MOS 6526 Complex Interface Adapter"
tags: [c64, hardware, cia, registers]
---

# CIA Chips — MOS 6526 Complex Interface Adapter

The Commodore 64 uses two MOS 6526 CIA chips to handle I/O (Input/Output) operations, timers, and the real-time clock.

## CIA 1 ($DC00-$DC0F): Keyboard, Joysticks, and IRQ

CIA 1 is primarily responsible for the keyboard, joystick ports, and generating IRQ interrupts.

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| 0        | $DC00   | DATA A | Joystick 2 and keyboard column scan |
| 1        | $DC01   | DATA B | Joystick 1 and keyboard row scan |
| 2        | $DC02   | DDRA   | Data Direction Register A |
| 3        | $DC03   | DDRB   | Data Direction Register B |
| 4-5      | $DC04-5 | TIMER A | Timer A (Low/High byte) |
| 6-7      | $DC06-7 | TIMER B | Timer B (Low/High byte) |
| 13       | $DC0D   | ICR    | Interrupt Control and Status |
| 14       | $DC0E   | CRA    | Control Register A |
| 15       | $DC0F   | CRB    | Control Register B |

## CIA 2 ($DD00-$DD0F): VIC-II Bank, User Port, and NMI

CIA 2 handles the User Port, Serial Bus, and most importantly, VIC-II bank selection and NMI interrupts.

| Register | Address | Name | Description |
|----------|---------|------|-------------|
| 0        | $DD00   | DATA A | VIC-II Bank Select (bits 0-1), Serial Bus |
| 1        | $DD01   | DATA B | User Port |
| 13       | $DD0D   | ICR    | Interrupt Control and Status (NMI) |

### VIC-II Bank Selection ($DD00)

Bits 0 and 1 of $DD00 control which 16KB bank of memory the VIC-II chip "sees":

| Bits 0-1 | Bank | Range |
|----------|------|-------|
| %11 (3)  | 0    | $0000-$3FFF (Default) |
| %10 (2)  | 1    | $4000-$7FFF |
| %01 (1)  | 2    | $8000-$BFFF |
| %00 (0)  | 3    | $C000-$FFFF |

---

# Chip CIA — Adattatore di Interfaccia Complessa MOS 6526 (Italiano)

Il Commodore 64 utilizza due chip MOS 6526 CIA per gestire le operazioni di I/O (Input/Output), i timer e l'orologio in tempo reale.

## CIA 1 ($DC00-$DC0F): Tastiera, Joystick e IRQ

La CIA 1 è responsabile principalmente della tastiera, delle porte joystick e della generazione di interrupt IRQ.

| Registro | Indirizzo | Nome | Descrizione |
|----------|-----------|------|-------------|
| 0        | $DC00     | DATA A | Joystick 2 e scansione colonne tastiera |
| 1        | $DC01     | DATA B | Joystick 1 e scansione righe tastiera |
| 13       | $DC0D     | ICR    | Controllo e stato degli interrupt |

## CIA 2 ($DD00-$DD0F): Bank VIC-II, User Port e NMI

La CIA 2 gestisce la User Port, il Serial Bus e, cosa più importante, la selezione dei banchi VIC-II e gli interrupt NMI.

### Selezione Banco VIC-II ($DD00)

I bit 0 e 1 di $DD00 controllano quale banco di memoria da 16KB viene "visto" dal chip VIC-II:

| Bit 0-1  | Banco | Intervallo |
|----------|-------|------------|
| %11 (3)  | 0     | $0000-$3FFF (Default) |
| %10 (2)  | 1     | $4000-$7FFF |
| %01 (1)  | 2     | $8000-$BFFF |
| %00 (0)  | 3     | $C000-$FFFF |

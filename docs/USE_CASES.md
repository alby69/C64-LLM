# Casi d'Uso: C64 Coding Agent

Questi esempi mostrano come interagire con l'agente per ottenere i migliori risultati.

## 1. Generazione di una Routine Assembly (Raster Interrupt)

**Utente:** "Vorrei creare un raster interrupt che cambi il colore del bordo all'altezza della riga 100 dello schermo."

**Comportamento dell'Agente:**
1. **Researcher**: Cerca nei documenti VIC-II i registri `$D011`, `$D012` e `$D019`.
2. **Coder**:
    - Pianifica il setup: disabilita IRQ standard, imposta il vettore `$0314`.
    - Genera il codice ACME.
3. **Validator**: Compila con ACME. Se dimentica di pulire il flag di interrupt (`ASL $D019`), il Validator lo segnala e il Coder corregge.

**Esempio di Output:**
```assembly
* = $C000
SEI
LDA #$7F
STA $DC0D
LDA $D011
AND #$7F
STA $D011
LDA #100
STA $D012
LDA #<IRQ
STA $0314
LDA #>IRQ
STA $0315
LDA #$01
STA $D01A
CLI
RTS

IRQ:
INC $D020
ASL $D019
JMP $EA31
```

---

## 2. Programma BASIC con Gestione Dati

**Utente:** "Scrivi un programma BASIC che chieda il nome di 3 giocatori e i loro punteggi, poi li mostri in una classifica ordinata."

**Comportamento dell'Agente:**
1. **Coder**: Usa `DIM N$(3), S(3)` per i dati. Implementa un semplice bubble sort o inserimento ordinato.
2. **Validator**: Controlla che le variabili non collidano (es. `S1` e `S2` sono ok, ma `SCORE1` e `SCORE2` verrebbero segnalati come warning).

---

## 3. Risoluzione Errori (Self-Healing)

**Utente:** (Invia un codice con un errore di branch fuori range)

**Comportamento dell'Agente:**
1. **Validator**: "Branch 'BNE' verso 'TARGET' fuori range: 150 byte."
2. **Orchestrator**: Chiede al Coder di usare un `JMP` inverso.
3. **Output**: Fornisce la versione corretta:
```assembly
; Invece di BNE TARGET (lontano)
BEQ SKIP
JMP TARGET
SKIP:
```

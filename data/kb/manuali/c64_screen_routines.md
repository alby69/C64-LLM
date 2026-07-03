# C64 Screen Routines — Pulire lo Schermo (Clear Screen)

## 1. Assembly 6502 — Tramite KERNAL

### JSR $E544 (Clear Screen — KERNAL)
```
    JSR $E544        ; pulisce lo schermo e posiziona il cursore in home
```
L'indirizzo $E544 (58692 in decimale) è la routine ufficiale del KERNAL Commodore 64 che pulisce lo schermo. È il metodo più semplice e veloce in Assembly.

### JSR $FC58 (HOME — Clear Screen + Home)
```
HOME  EQU $FC58
      JSR HOME       ; pulisce lo schermo e sposta il cursore in alto a sinistra
```
$FC58 è la routine HOME del KERNAL. Svuota lo schermo e riporta il cursore in posizione (0,0).

### LDA #$93 / JSR $FFD2 (Clear Screen via CHROUT)
```
      LDA #$93       ; codice CHR$ 147 = clear screen
      JSR $FFD2      ; KERNAL CHROUT — stampa il carattere
```
$93 (147 decimale) è il codice del carattere di controllo "CLEAR HOME" del C64. Inviandolo via $FFD2 (CHROUT), il KERNAL pulisce lo schermo.

**NOTA:** JSR $FFD2 è la routine standard per output di un carattero. Funziona come PRINT in BASIC.

---

## 2. Assembly 6502 — Tramite Riempimento Directo della Screen RAM

### Fill Screen RAM con Spazi ($0400-$07E7)
```
; Pulire lo schermo riempiendo la memoria video con spazi ($20)
; La Screen RAM occupa $0400-$07E7 (1000 byte = 40x25 caratteri)

      LDA #$20       ; carattere spazio (codice screen PETASCII)
      LDX #0
LOOP  STA $0400,X    ; prima parte: $0400-$04FF
      STA $0500,X    ; seconda parte: $0500-$05FF
      STA $0600,X    ; terza parte: $0600-$06FF
      STA $06E8,X    ; quarta parte: $06E8-$07E7 (fino a 999)
      INX
      BNE LOOP       ; loop 256 volte per ogni blocco
      RTS
```

### Versione con Puntatore Indiretto
```
; Pulire lo schermo con puntatore indiretto (più compatto)

PTR   EQU $06        ; puntatore zero page (2 byte)
ENTRY LDA #$04       ; high byte di screen base $0400
      STA PTR+1
      LDY #0
      STY PTR        ; low byte = 0
START LDA #$A0       ; spazio (codice screen C64, $20 è spazio normale)
LOOP  STA (PTR),Y
      INY
      BNE LOOP
NXT   INC PTR+1
      LDA PTR+1
      CMP #$08       ; fino a $0800 (dopo $07FF)
      BCC START
EXIT  RTS
```

**NOTA:** La Screen RAM va da $0400 a $07E7 (1000 byte). In Assembly, si possono usare 4 loop da 256 byte ciascuno o un puntatore a 16 bit. Il Color RAM ($D800-$DBE7) non va toccata se si vuole mantenere i colori esistenti.

---

## 3. BASIC v2 — Pulire lo Schermo

### PRINT CHR$(147)
```
10 PRINT CHR$(147)   :REM PULISCE LO SCHERMO
```
Il codice 147 corrisponde a CLR/HOME. In BASIC si usa PRINT CHR$() per inviarlo.

### SYS (per chiamare routine Assembly precaricate)
```
10 SYS 58692         :REM EQUIVALE A JSR $E544 (CLEAR SCREEN VIA KERNAL)
```
**ATTENZIONE:** SYS è un comando BASIC, non un'istruzione Assembly. Chiama una routine in linguaggio macchina già presente in memoria. $E544 = 58692 è la routine KERNAL che pulisce lo schermo.

---

## 4. Riepilogo Metodi

| Metodo | Tipo | Byte | Indirizzo | Note |
|--------|------|------|-----------|------|
| JSR $E544 | Assembly | 3 | $E544 | KERNAL ufficiale, rapido |
| JSR $FC58 | Assembly | 3 | $FC58 | HOME + clear screen |
| LDA #$93 / JSR $FFD2 | Assembly | 4 | $FFD2 | Usa CHROUT |
| Fill $0400-$07E7 | Assembly | ~24 | — | Piu' veloce, nessuna dipendenza ROM |
| PRINT CHR$(147) | BASIC | — | — | Standard in BASIC v2 |

---

## 5. Errori Comuni

- **SYS $0002** non esiste e non fa nulla di utile: $0002 è in Zero Page, area dati, non codice.
- **SYS $FCE2** è la routine KERNAL "cold start", non pulisce lo schermo.
- **POKE 53280,0** cambia solo il colore del bordo, non pulisce lo schermo.
- Confondere SYS (BASIC) con JSR (Assembly): SYS si usa in BASIC, JSR in Assembly.

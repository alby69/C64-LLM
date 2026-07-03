# Raster Interrupts — Interrupt al Raster sul C64

Il raster interrupt è la tecnica fondamentale per sincronizzare il codice con il ciclo di scansione video del VIC-II. Permette di cambiare registri grafici in punti precisi dello schermo (split screen, barre multicolore, scrolling diviso).

## Come Funziona

Il VIC-II genera un interrupt quando la riga raster corrente raggiunge un valore programmato in $D012. Il vettore di interrupt ($0314/$0315) deve puntare alla nostra routine.

## Sequenza Base

### 1. Impostare il raster interrupt
```
      sei           ; disabilita interrupt durante il setup
      lda #<my_irq
      sta $0314     ; vettore IRQ low byte
      lda #>my_irq
      sta $0315     ; vettore IRQ high byte
      lda #$01
      sta $D01A     ; abilita raster interrupt
      lda #100      ; riga raster target (0-255, riga 100)
      sta $D012
      lda $D011
      and #$7F      ; azzera bit 7 (MSB raster = 0)
      sta $D011
      cli           ; riabilita interrupt
      rts
```

### 2. La routine di interrupt
```
my_irq:
      ; qui puoi cambiare registri VIC-II
      inc $D020     ; cambia colore bordo

      ; se è uno split, imposta la prossima riga raster
      lda #180
      sta $D012     ; prossimo interrupt a riga 180

      ; riconoscimento interrupt: pulisci il flag
      asl $D019     ; $D019 bit 0 = 1 → azzera scrivendo 1

      ; return dall'interrupt KERNAL
      jmp $EA81     ; IRQ handler standard (salva registri, ripristina, RTI)
```

## Multipla Raster (Split Screen)

```
; Due raster interrupt: riga 80 e riga 160

init:
      sei
      lda #<irq_80
      sta $0314
      lda #>irq_80
      sta $0315
      lda #$01
      sta $D01A
      lda #80
      sta $D012
      cli
      rts

irq_80:
      ; cambio colore per la parte superiore
      lda #$02       ; rosso
      sta $D020

      ; imposta il prossimo interrupt a riga 160
      lda #160
      sta $D012

      ; reindirizza il vettore per la prossima volta
      lda #<irq_160
      sta $0314
      lda #>irq_160
      sta $0315

      asl $D019
      jmp $EA31

irq_160:
      ; cambio colore per la parte inferiore
      lda #$05       ; verde
      sta $D020

      ; torna all'interrupt di riga 80
      lda #80
      sta $D012

      lda #<irq_80
      sta $0314
      lda #>irq_80
      sta $0315

      asl $D019
      jmp $EA31
```

## Raster con Riga > 255

Per raster oltre la riga 255 serve il bit 7 di $D011:
```
      ; raster = riga 300 ($012C)
      lda #$2C      ; low byte = $2C
      sta $D012
      lda $D011
      ora #$80      ; setta bit 7 (MSB)
      sta $D011
```

## $EA81 vs $EA31

Due modi di terminare un raster interrupt:

| Routine | Effetto |
|---------|---------|
| **JMP $EA81** | Salva A,X,Y, ripristina registri, RTI. Usa lo stack KERNAL completo. |
| **JMP $EA31** | Salva A,X,Y, controlla se altro interrupt (NMI, CIA). Piu' veloce e stabile per raster multipli. |

$EA31 è raccomandato per raster interrupt multipli. $EA81 è più generico e sicuro.

## Errori Comuni

- **Dimenticare ASL $D019** — senza riconoscimento, l'interrupt riesplode immediatamente in loop.
- **Non salvare/ripristinare i registri** — il VIC-II non lo fa automaticamente, serve JMP $EA81/$EA31.
- **SEI senza CLI** — se la CPU rimane con interrupt disabilitati, niente funziona.
- **Riga raster sbagliata** — lo schermo PAL è 312 righe totali, visibili solo 200 (righe 50-249). I valori fuori range non generano interrupt.

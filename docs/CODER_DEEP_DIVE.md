# Deep Dive: CoderAgent

Il `CoderAgent` è l'agente esecutivo specializzato nella sintesi di codice funzionale per il Commodore 64.

## Come Lavora (Flusso Attuale)

1.  **Integrazione del Context Brief**:
    - Riceve dal Researcher un insieme di informazioni tecniche filtrate (registri, indirizzi, routine KERNAL).
    - Queste informazioni agiscono come "ancora" per evitare allucinazioni su indirizzi di memoria critici.

2.  **Ragionamento Strutturato (Chain-of-Thought)**:
    - Il prompt di sistema obbliga l'agente a seguire un percorso logico:
        - **Analisi**: Identifica i vincoli (es. "devo usare l'interruzione IRQ").
        - **Pianificazione**: Definisce i passi (es. "1. Disabilita interruzioni, 2. Cambia vettore $0314, 3. Riabilita").
        - **Implementazione**: Produce il codice effettivo.
    - Questo approccio riduce gli errori logici comuni nella programmazione assembly.

3.  **Gestione delle Personalità (C64 Expert Profiles)**:
    - In base al contesto rilevato, il Coder assume una 'Personalità' specifica tramite il **PMS**:
        - **BASIC V2 Expert**: Bassa memoria, variabili corte, sintassi standard.
        - **6510 Assembly Expert**: Ottimizzazione cicli macchina, sintassi ACME.
    - La temperatura viene adattata dinamicamente (0.2 per ASM, 0.4 per BASIC).

## Punti di Forza
- **Affidabilità Sintattica**: Grazie alla bassa temperatura e alla validazione a valle dell'Orchestratore.
- **Auto-correzione Inviata**: Fornendo una struttura di "Revisione" interna, l'agente spesso identifica da solo piccoli errori prima di terminare la generazione.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Ottimizzatore di Cicli (Cycle Counter)**:
    - Un modulo che analizza il codice generato e suggerisce alternative più veloci (es. usare `LSR` invece di `DIV` o tabelle di look-up).

2.  **Linter Simbolico**:
    - Verificare che tutte le etichette siano definite e che non ci siano sovrapposizioni tra segmenti di memoria.

3.  **Few-Shot Dinamici dal Knowledge Engine**:
    - Recuperare piccoli snippet di codice "perfetti" basati sulla query per migliorare lo stile e la correttezza del codice generato.

4.  **Global Memory Mapping**:
    - Un sistema per riservare aree di memoria tra diverse turnazioni di chat, evitando conflitti di indirizzi.

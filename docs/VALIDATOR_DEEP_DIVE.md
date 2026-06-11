# Deep Dive: ValidatorAgent

Il `ValidatorAgent` è il "guardiano" della qualità del codice prodotto, incaricato di verificare che gli snippet generati siano effettivamente eseguibili o sintatticamente corretti per l'ambiente Commodore 64.

## Come Lavora (Flusso Attuale)

1.  **Estrazione del Codice**:
    - Utilizza espressioni regolari per individuare blocchi di codice Markdown nella risposta dell'LLM.
    - Gestisce tag specifici come `assembly`, `asm`, `6502` o blocchi generici.

2.  **Classificazione Euristica**:
    - Analizza il contenuto del blocco per distinguere tra Assembly e BASIC.
    - Se trova istruzioni come `LDA`, `STA`, `JSR`, lo classifica come Assembly.

3.  **Validazione Esterna (Assembly)**:
    - Per l'Assembly, si interfaccia con `utils/validate_emulator.py` che a sua volta richiama l'assemblatore **ACME**.
    - Cattura l'output dell'assemblatore per identificare errori di sintassi, etichette mancanti o istruzioni illegali.

4.  **Validazione BASIC (Limitata)**:
    - Attualmente, il codice BASIC viene rilevato ma non validato attivamente (ritorna sempre `True`).

## Punti di Forza
- **Feedback Loop**: Fornisce log di errore dettagliati che l'Orchestratore può usare per richiedere correzioni all'LLM.
- **Prevenzione Errori**: Impedisce che codice palesemente errato venga presentato come soluzione definitiva.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Parser BASIC v2**:
    - Implementare un validatore sintattico per il BASIC che controlli la numerazione delle righe, la chiusura dei cicli `FOR/NEXT` e la correttezza dei comandi.

2.  **Analisi Statica Assembly**:
    - Controllare i "range" dei salti relativi (branch) e segnalare se superano i 127 byte, un errore comune per gli LLM.
    - Verificare l'uso di indirizzi di memoria "proibiti" o riservati dal KERNAL.

3.  **Validazione del Flusso Logico**:
    - Oltre alla compilazione, potrebbe eseguire piccoli test funzionali (es. "il codice finisce con un RTS?") per garantire che lo snippet non lasci il C64 in uno stato instabile.

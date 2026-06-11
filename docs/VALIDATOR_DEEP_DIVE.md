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

4.  **Validazione BASIC v2**:
    - Implementa un parser sintattico interno che verifica:
        - Presenza e formato dei numeri di riga.
        - Bilanciamento dei cicli `FOR/NEXT`.
        - Presenza di parole chiave BASIC v2.

## Punti di Forza
- **Feedback Loop**: Fornisce log di errore dettagliati che l'Orchestratore può usare per richiedere correzioni all'LLM.
- **Prevenzione Errori**: Impedisce che codice palesemente errato venga presentato come soluzione definitiva.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Interprete BASIC Integrato**:
    - Collegare un interprete BASIC v2 minimale per verificare non solo la sintassi, ma anche la logica di base (evitare `SYNTAX ERROR` a runtime).

2.  **Analisi Statica Avanzata Assembly**:
    - Controllare i "range" dei salti relativi (branch).
    - Verificare l'uso di indirizzi di memoria riservati dal KERNAL che potrebbero causare crash.

3.  **Unit Testing del Codice Generato**:
    - Eseguire lo snippet in un ambiente emulato e verificare lo stato dei registri o della memoria dopo l'esecuzione (es: "il colore del bordo è diventato rosso?").

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

3.  **Ottimizzazione dei Parametri**:
    - Utilizza una temperatura estremamente bassa (0.2) per il codice Assembly 6502, dove la precisione sintattica è vitale.
    - Utilizza una temperatura leggermente più alta (0.4) per il BASIC v2 o per spiegazioni testuali, dove una maggiore fluidità linguistica è utile.

## Punti di Forza
- **Affidabilità Sintattica**: Grazie alla bassa temperatura e alla validazione a valle dell'Orchestratore.
- **Auto-correzione Inviata**: Fornendo una struttura di "Revisione" interna, l'agente spesso identifica da solo piccoli errori prima di terminare la generazione.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Ottimizzatore di Cicli (Cycle Counter)**:
    - Un modulo che analizza il codice generato e suggerisce alternative più veloci (es. usare `LSR` invece di `DIV` o tabelle di look-up per calcoli complessi).

2.  **Linter Assembly Integrato**:
    - Prima di passare il codice al Validator, il Coder potrebbe far passare il sorgente attraverso un linter simbolico per verificare che tutte le etichette siano definite.

3.  **Esempi "Few-Shot" Dinamici**:
    - Il Researcher potrebbe recuperare non solo documentazione, ma anche piccoli snippet di codice "perfetti" come esempi per il Coder, migliorando la coerenza dello stile.

4.  **Gestione della Memoria (Memory Mapping)**:
    - Un sistema per tenere traccia delle aree di memoria occupate dal codice generato durante la sessione, per evitare che snippet successivi sovrascrivano quelli precedenti (fondamentale per programmi multi-modulo).

# Deep Dive: OrchestratorAgent

L' `OrchestratorAgent` è il "regista" del sistema. Gestisce il ciclo di vita di una richiesta utente, delegando compiti specifici agli altri agenti e gestendo il flusso di informazioni tra di loro.

## Come Lavora (Flusso Attuale)

1.  **Fase di Ricerca (Delega al Researcher)**:
    - Se il RAG è abilitato, invia la query al Researcher per ottenere il contesto tecnico.
    - Gestisce la query espansa e i frammenti di documentazione recuperati.

2.  **Fase di Generazione (Delega al Coder)**:
    - Passa la query originale e il contesto tecnico al Coder.
    - Riceve la risposta strutturata (Analisi, Piano, Codice, Revisione).

3.  **Fase di Controllo Qualità (Delega al Validator)**:
    - Invia l'output del Coder al Validator per la verifica formale del codice.

4.  **Self-Healing (Recupero Errori)**:
    - Se il Validator segnala errori, l'Orchestratore non si arrende.
    - Costruisce un nuovo prompt di "correzione" includendo i log di errore dell'assemblatore e lo invia nuovamente al Coder.
    - Effettua un secondo round di validazione.

## Punti di Forza
- **Resilienza**: Il meccanismo di self-healing corregge spesso piccoli errori di battitura o sintassi tipici degli LLM.
- **Modularità**: Può facilmente attivare o disattivare il RAG a seconda della necessità.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Ragionamento Multi-Passo (Multi-step Reasoning)**:
    - Se una richiesta è complessa (es: "scrivi un gioco completo"), l'Orchestratore potrebbe scomporla in sotto-task e gestire più cicli di generazione/validazione.

2.  **Gestione dello Stato (Context Memory)**:
    - Mantenere una sessione coerente che ricordi le aree di memoria già assegnate (Memory Mapping) per evitare conflitti tra diversi snippet.

3.  **Ottimizzazione Backend Dinamica**:
    - Scegliere il backend più adatto (es: Transformers per precisione se disponibile GPU, LlamaCpp per velocità su CPU) in modo trasparente.

4.  **Agenti Specializzati Aggiuntivi**:
    - Integrare agenti per task grafici (Sprite Editor) o sonori (SID Composer) per scomposizioni di task complessi.

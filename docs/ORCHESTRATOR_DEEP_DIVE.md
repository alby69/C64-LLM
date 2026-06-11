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

2.  **Gestione dello Stato (Memory Management)**:
    - Mantenere una "mappa della memoria" globale per evitare che diversi agenti suggeriscano di usare le stesse aree di RAM per scopi diversi nella stessa sessione.

3.  **Selezione Dinamica del Modello**:
    - Potrebbe decidere di usare parametri diversi (es: temperatura più alta per spiegazioni creative, più bassa per routine critiche) a seconda della fase del processo.

4.  **Integrazione Obsidian-Wiki**:
    - Diventare il navigatore principale del grafo di conoscenza, chiedendo al Researcher di esplorare nodi correlati se la ricerca iniziale è povera.

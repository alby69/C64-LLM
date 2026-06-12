# Deep Dive: ResearcherAgent

Il `ResearcherAgent` è il componente critico che garantisce che il `CoderAgent` non lavori "nel vuoto", ma sia supportato da documentazione tecnica accurata.

## Come Lavora (Flusso Attuale)

1.  **Analisi & Espansione (Query Expansion)**:
    - Traduce la richiesta dell'utente in termini tecnici C64 (es: "cambio colore bordo" -> "$D020, VIC-II, border color, register") usando l'LLM e i prompt centralizzati nel PMS.

2.  **Rilevamento del Linguaggio (ASM vs BASIC)**:
    - Pre-classifica la richiesta per filtrare i documenti e orientare la "personalità" del Coder. Se l'utente chiede BASIC, il Researcher dà priorità alla documentazione relativa.

3.  **Ricerca Ibrida & Navigazione del Grafo (Obsidian Engine)**:
    - **Ricerca Vettoriale**: Utilizza FAISS per trovare i frammenti più simili alla query.
    - **Navigazione Wiki-links**: Se un frammento trovato contiene link come `[[Raster Interrupt]]`, il Researcher esplora automaticamente questi nodi correlati per arricchire il contesto.
    - **Frontmatter & Tag**: Sfrutta i metadati YAML delle note Markdown per affinare la pertinenza.

4.  **Sintesi del Context Brief**:
    - Combina i frammenti trovati in un blocco strutturato, citando le sorgenti consultate.

## Punti di Forza dell'Implementazione "Opzione A"
- **Zero Overhead di Memoria**: Condividendo l'istanza del modello con il Coder, il Researcher non occupa RAM aggiuntiva.
- **Precisione Tecnica**: L'espansione della query riduce drasticamente il rischio di non trovare informazioni presenti ma scritte con un linguaggio diverso da quello dell'utente.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Reranking (Cross-Encoding)**:
    - Implementare un modulo di reranking per selezionare i frammenti con la massima pertinenza semantica dopo la prima fase di ricerca vettoriale.

2.  **HyDE (Hypothetical Document Embeddings)**:
    - Generare una "risposta ipotetica" e usare quella per la ricerca, migliorando il matching con i documenti tecnici.

3.  **Multi-turn Memory**:
    - Integrare la cronologia della conversazione per mantenere il contesto nelle query successive (es: "e ora cambia anche il colore dello sfondo").

4.  **Integrazione Web (Implementato)**:
    - Tramite il `WebCrawlerAgent`, il sistema può ora acquisire proattivamente documentazione da Archive.org per colmare le lacune del Knowledge Base locale.

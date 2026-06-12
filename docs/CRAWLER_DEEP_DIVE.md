# Deep Dive: WebCrawlerAgent (Knowledge Acquisition)

Il `WebCrawlerAgent` è il componente proattivo del sistema, progettato per espandere autonomamente il Knowledge Base attingendo da fonti autorevoli sul web.

## Missione
A differenza del `ResearcherAgent` che è reattivo (cerca risposte a domande specifiche), il `WebCrawlerAgent` ha l'obiettivo di "mappare" la conoscenza storica e tecnica del Commodore 64, trasformando manuali, libri e articoli in note strutturate per Obsidian.

## Flusso di Lavoro (Pipeline)

1.  **Discovery (Archive.org API)**:
    - Utilizza la libreria `internetarchive` per cercare documenti tecnici basati su parole chiave (es. "6502 assembly", "Commodore 64 programmer's reference").
    - Filtra per `mediatype:texts` per garantire la presenza di documenti leggibili.

2.  **Acquisizione (PDF Processing)**:
    - Scarica i file PDF in una directory temporanea (`data/tmp`).
    - Utilizza `PyMuPDF` (metodo `blocks`) per estrarre il testo. Questo metodo è scelto per la sua robustezza nel gestire layout multi-colonna tipici delle riviste anni '80.

3.  **Trasformazione Intelligente (LLM-based)**:
    - Il testo estratto viene inviato all'LLM (Qwen2.5-Coder) con un prompt specializzato (`crawler.transform.system`).
    - **Compiti dell'LLM**:
        - Generare un frontmatter YAML con categorie, tag e topic.
        - Identificare entità tecniche e creare `[[Wiki-links]]` automatici.
        - Formattare eventuali listati di codice in blocchi Markdown.
        - Strutturare il contenuto con intestazioni coerenti.

4.  **Archiviazione Obsidian**:
    - Salva la nota generata nella cartella corretta all'interno di `knowledge_base/` (es. `knowledge_base/Hardware/`, `knowledge_base/Assembly/`).
    - La nota è immediatamente pronta per essere visualizzata nel grafo di Obsidian e indicizzata dal sistema RAG.

## Integrazione con il Sistema
Il Crawler agisce come alimentatore per il `ResearcherAgent`. Più il Crawler "esplora", più il Researcher diventa preciso grazie alla densità di collegamenti (Wiki-links) creati nel grafo.

## Sviluppi Futuri
- **Scraping di Wiki/Forum**: Estendere il supporto a C64-Wiki e Codebase64.
- **Deduplicazione Semantica**: Verificare se una nota simile esiste già prima di crearne una nuova.
- **Recursive Crawling**: Seguire i link citati nei documenti per scaricare ulteriori risorse correlate.

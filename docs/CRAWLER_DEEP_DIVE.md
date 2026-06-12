# Deep Dive: WebCrawlerAgent (Knowledge Acquisition)

Il `WebCrawlerAgent` è il componente proattivo del sistema, progettato per espandere autonomamente il Knowledge Base attingendo da fonti autorevoli sul web.

## Missione
A differenza del `ResearcherAgent` che è reattivo (cerca risposte a domande specifiche), il `WebCrawlerAgent` ha l'obiettivo di "mappare" la conoscenza storica e tecnica del Commodore 64, trasformando manuali, libri e articoli in note strutturate per Obsidian.

## Gestione delle Fonti
L'agente non "vaga" a caso nel web, ma monitora una lista di **Sorgenti Autorevoli** definita nel file di configurazione centrale:
- **Percorso**: `config/crawler_sources.yaml`
Le fonti supportate includono:
- **C64-Wiki**: Documentazione enciclopedica.
- **Codebase64**: Tutorial tecnici e demoscene.
- **Zimmers.net**: Archivi di mappe e file storici.
- **Archive.org**: Libri e manuali originali (PDF).
- **GitHub**: Repository di riferimento (es. mist64/c64ref).

## Interfaccia tra Agenti
Il `WebCrawlerAgent` lavora "dietro le quinte" per alimentare il sistema:
1. **Crawler**: Scopre nuovi PDF o articoli -> Li trasforma in Markdown Obsidian.
2. **Knowledge Base**: Indicizza i nuovi file Markdown, i loro tag e i Wiki-links.
3. **Researcher**: Quando l'utente fa una domanda, il Researcher trova i collegamenti nel grafo creato dal Crawler.
4. **Coder**: Riceve il contesto arricchito (es. registri SID o mappe di memoria) per generare codice accurato.

## Flusso di Lavoro (Pipeline)

1.  **Discovery (Source Monitoring)**:
    - Legge `config/crawler_sources.yaml` e controlla lo stato in `data/config/crawler_status.json` per identificare fonti nuove o aggiornate.
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

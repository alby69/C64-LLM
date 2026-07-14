# Proposta di Snellimento di C64-LLM e Integrazione con C64-KB-Agent

Questo documento descrive in dettaglio la strategia di refactoring per disaccoppiare, semplificare e ottimizzare l'architettura di **C64-LLM**, delegando l'acquisizione dei dati interamente a **C64-Scrapy** e la standardizzazione a **C64-KB-Agent** (che diventa l'unica fonte di conoscenza autorevole), in linea con la filosofia Unix **KISS** (*Keep It Simple, Stupid*) e **DRY** (*Don't Repeat Yourself*).

---

## 1. Analisi dello Stato dell'Ecosistema

Attualmente, l'ecosistema C64 è composto da tre repository principali:
1.  **C64-Scrapy**: Motore specializzato nell'acquisizione proattiva di pagine web, documentazione e wiki tecnici tramite spider Scrapy.
2.  **C64-KB-Agent**: Hub di storage e standardizzazione della Knowledge Base. Pulisce i metadati, gestisce il frontmatter YAML e organizza i file Markdown in strutture pulite e unificate.
3.  **C64-LLM** (Questo Repo): Motore di ragionamento multi-agente, RAG (FAISS) ed esecuzione di codice (con simulatore `py6502` e compilazione ACME).

### Il Problema: Duplicazione delle Responsabilità e Violazione del Principio DRY
Nello stato attuale, `C64-LLM` contiene al suo interno:
- Un intero `WebCrawlerAgent` (`agent/crawler.py`) per scaricare documenti da Archive.org e Google Drive.
- Diversi script di scraping indipendenti in `pipeline/` (`c64_asm_scraper.py`, `scrape_docs.py`, `scrape_url.py`, `run_crawler.py`).
- Molteplici dipendenze pesanti e moduli di scraping ridondanti che replicano quanto già fatto in modo molto più robusto da `C64-Scrapy` e `C64-KB-Agent`.

Questo approccio causa:
- **Desincronizzazione della conoscenza**: LLM e KB-Agent mantengono copie o indici diversi.
- **Instabilità**: I crawler inclusi nell'LLM sono difficili da mantenere e sensibili a modifiche del layout web.
- **Accoppiamento Forte**: L'interfaccia utente dell'LLM (Gradio) lancia direttamente questi script legacy locali, rendendo il codice fragile.

---

## 2. Il Piano di Snellimento (KISS & DRY)

Per risolvere questi problemi e garantire un disaccoppiamento pulito, implementiamo le seguenti azioni:

### A. Rimozione dei Servizi Ridondanti in `C64-LLM`
Eliminiamo completamente i seguenti componenti dal repository `C64-LLM`:
1.  `agent/crawler.py` (Rimosso: la logica di crawling spetta a `C64-Scrapy`).
2.  `pipeline/run_crawler.py` (Rimosso).
3.  `pipeline/c64_asm_scraper.py` (Rimosso).
4.  `pipeline/scrape_docs.py` (Rimosso).
5.  `pipeline/scrape_url.py` (Rimosso).

### B. C64-KB-Agent come Unica Base di Conoscenza Autorevole
La pipeline di RAG di `C64-LLM` viene semplificata. Non tenta più di scaricare o pulire file di testo grezzi. Consuma direttamente i documenti standardizzati in formato Markdown prodotti da `C64-KB-Agent`.
L'integrazione avviene tramite il **ScrapyKBAdapter** (`pipeline/acquisition/scrapy_kb_adapter.py`):
- **Sync**: Copia i file Markdown validati da `C64-KB-Agent` in `data/kb/scraped/` confrontando gli hash MD5 per un'ingestione incrementale ed efficiente.
- **Execution**: Consente di lanciare programmaticamente gli spider di `C64-Scrapy` per alimentare la KB in modo centralizzato.
- **Local FAISS Cache**: L'LLM mantiene il proprio indice FAISS ultra-veloce (in `data/vectorstore/`), che viene ricostruito su richiesta partendo dai file sincronizzati.

---

## 3. Riorganizzazione dell'Interfaccia Utente (Gradio UI)

Il tab legacy **"Scarica e Siti"** dell'interfaccia Gradio (`agent/agent_pro.py`) viene rimpiazzato con il nuovo tab **"Integrazione C64-KB-Agent"**, strutturato secondo i seguenti principi:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      INTEGRAZIONE C64-KB-Agent                         │
├────────────────────────────────────────────────────────────────────────┤
│  [ Sincronizza KB da C64-KB-Agent ]  -> ScrapyKBAdapter.sync()         │
│  [ Avvia Spider C64-Scrapy ]         -> ScrapyKBAdapter.run_spider()    │
│  [ Ricostruisci Indice RAG ]         -> C64KnowledgeBase.build_index()  │
├────────────────────────────────────────────────────────────────────────┤
│  Log di Sincronizzazione ed Esecuzione                                 │
└────────────────────────────────────────────────────────────────────────┘
```

Questo approccio offre:
- Un'esperienza utente coerente con la realtà multi-repo.
- Visibilità immediata del flusso dei dati.
- Azioni esplicite di sincronizzazione e aggiornamento dell'indice.

---

## 4. Automazione tramite GitHub Actions

Per completare il disaccoppiamento ed evitare interventi manuali continui, introduciamo un workflow di GitHub Actions in `C64-LLM` (`.github/workflows/kb_sync.yml`).

Questo workflow automatizza due flussi chiave:
1.  **Aggiornamento Schedulato / Trigger**: Ricostruisce periodicamente l'indice FAISS dell'LLM quando vengono fatti push di nuovi documenti in `C64-KB-Agent`.
2.  **Verifica Integrazione**: Esegue i test di integrazione per assicurarsi che i file Markdown sincronizzati dal KB-Agent vengano indicizzati correttamente dall'LLM.

---

## 5. Vantaggi del Nuovo Approccio

- **Semplificazione del Codice**: Rimozione di centinaia di righe di codice di scraping instabile ed obsoleto.
- **Risoluzione della Doppia Gestione**: La conoscenza è centralizzata in `C64-KB-Agent`. L'LLM si occupa solo del RAG e del ragionamento.
- **Modularità Unix**: Ogni strumento fa una sola cosa e la fa bene. `C64-Scrapy` estrae, `C64-KB-Agent` organizza, `C64-LLM` risponde.

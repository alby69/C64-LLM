# Piano di Refactoring C64-LLM

Questo documento delinea la strategia per un refactoring pesante di C64-LLM, volto a disaccoppiare i moduli, semplificare la struttura dei dati e facilitare l'integrazione di strumenti esterni come **C64-Scrapy**.

## 1. Obiettivi del Refactoring

1.  **Disaccoppiamento Acquisizione/Processamento**: Separare nettamente la fase di scaricamento (Scraping/Crawling) dalla fase di trasformazione (Parsing/Cleaning).
2.  **Semplificazione `data/`**: Ridurre la complessità delle directory per eliminare ridondanze.
3.  **Modularità**: Trasformare la cartella `pipeline/` in un package Python strutturato con interfacce chiare.
4.  **Estendibilità**: Facilitare l'aggiunta di nuovi scraper o motori di ricerca senza modificare il core dell'agente.

## 2. Nuova Struttura dei Dati (Minimalista)

La cartella `data/` verrà riorganizzata come segue:

- `data/raw/`: Tutti i file originali non elaborati (PDF, D64, G64, PRG). Sostituisce `data/input/`.
- `data/kb/`: Documenti Markdown pronti per il RAG. Include l'output di Scrapy, Marker e i manuali curati. Sostituisce `data/output/` e integra `knowledge_base/`.
- `data/models/`: Modelli GGUF, LoRA adapter e configurazioni del backend.
- `data/db/`: Database vettoriale FAISS e metadati persistenti. Sostituisce `data/vectorstore/`.
- `data/logs/`: Log di esecuzione e stati dei crawler.

**Nota**: Le cartelle `tmp/` e `src/` verranno eliminate. I download temporanei andranno in `data/raw/.tmp/`.

## 3. Riorganizzazione Modulo `pipeline`

Il modulo `pipeline/` diventerà un package con la seguente gerarchia:

```text
pipeline/
├── __init__.py
├── base.py                 # Classi base e Interfacce (Provider, Extractor)
├── acquisition/            # Gestione sorgenti esterne
│   ├── archive_org.py      # Refactoring di agent/crawler.py
│   ├── google_drive.py     # Refactoring della logica in agent_pro.py
│   ├── scrapy_wrapper.py   # Adapter per C64-Scrapy
│   └── legacy_scraper.py   # Wrapper per c64_asm_scraper.py (fino a dismissione)
├── processing/             # Trasformazione dati
│   ├── extractors/         # D64, G64, PRG, PDF (Marker)
│   ├── cleaners/           # TextCleaner logic
│   └── factory.py          # Seleziona l'estrattore in base all'estensione
└── distillation/           # Generazione dataset
    └── builder.py          # Logic di build_dataset.py e distiller
```

## 4. Disaccoppiamento degli Agenti

- **WebCrawlerAgent**: Verrà rimosso da `agent/` e le sue funzionalità spostate in `pipeline/acquisition/`. L'agente Orchestrator richiamerà le API del modulo acquisition.
- **RAG Engine**: `agent/knowledge_base.py` verrà semplificato per concentrarsi solo sull'indicizzazione di `data/kb/`, delegando tutto il processamento preventivo al modulo `processing`.

## 5. Fasi di Implementazione

1.  **Fase 1**: Creazione delle nuove cartelle in `data/` e migrazione dei file esistenti.
2.  **Fase 2**: Refactoring del modulo `processing` e creazione della `ExtractorFactory`.
3.  **Fase 3**: Integrazione di **C64-Scrapy** tramite `pipeline/acquisition/scrapy_wrapper.py`.
4.  **Fase 4**: Spostamento della logica di crawling da `agent/` a `pipeline/` e pulizia del codice ridondante.
5.  **Fase 5**: Aggiornamento della UI (Gradio) per puntare ai nuovi moduli.

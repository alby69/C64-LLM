# Architettura e Compiti del C64-LLM

Questo documento descrive in dettaglio le responsabilità e l'organizzazione attuale del progetto C64-LLM, propedeutico al piano di refactoring e integrazione con C64-Scrapy.

## 1. Responsabilità Core

C64-LLM non è un semplice modello linguistico, ma un ecosistema completo per lo sviluppo e la preservazione del software Commodore 64. I suoi compiti principali sono suddivisi in cinque aree funzionali:

### 1.1 Acquisizione della Conoscenza (Data Acquisition)
- **Scraping Mirato**: Estrazione di codice Assembly da fonti autorevoli (Codebase64, 6502.org) tramite `c64_asm_scraper.py`.
- **Crawling Proattivo**: Monitoraggio di Archive.org per il download di manuali tecnici e libri in formato PDF/TXT/EPUB tramite `agent/crawler.py`.
- **Ingestion Flessibile**: Supporto per URL singoli, cartelle Google Drive e caricamento manuale di file PDF, D64, G64 e PRG.

### 1.2 Elaborazione e Trasformazione (Data Processing)
- **Detokenizzazione BASIC**: Conversione di file binari .PRG in listati BASIC v2 leggibili.
- **Analisi Linguaggio Macchina**: Generazione di hex dump e disassemblati di base per blocchi ML.
- **Conversione Documentale**: Trasformazione di PDF complessi in Markdown strutturato con layout detection (via `pdf2marker.py`).
- **Pulizia Testuale**: Normalizzazione dei testi estratti per rimuovere artefatti OCR e rumore tramite `text_cleaner.py`.

### 1.3 Knowledge Engine (RAG)
- **Indicizzazione Vettoriale**: Creazione di un database FAISS utilizzando embedding `sentence-transformers` per il recupero semantico.
- **Gestione Vault**: Organizzazione della documentazione in stile Obsidian con frontmatter YAML e Wiki-links.
- **Grafo della Conoscenza**: Rappresentazione visuale delle connessioni tra documenti tecnici (VIC-II, SID, Kernal, etc.).

### 1.4 Orchestrazione Multi-Agente
- **Researcher**: Espansione delle query e recupero del contesto tecnico dal RAG.
- **Coder**: Generazione di codice specializzato in BASIC v2 o Assembly 6502 usando Chain-of-Thought.
- **Validator**: Verifica sintattica rigorosa, stima dei cicli di clock e compilazione via ACME.
- **Orchestrator**: Gestione del ciclo di "Self-Healing" (fino a 3 tentativi) per correggere automaticamente errori di validazione.

### 1.5 Specializzazione del Modello (Training)
- **Knowledge Distillation**: Generazione di dataset sintetici Q&A (Teacher->Student) basati sulla Knowledge Base locale.
- **Fine-Tuning LoRA**: Addestramento del modello (Qwen2.5-Coder) per migliorare la precisione nel dominio C64.

---

## 2. Struttura delle Directory Attuale

Il progetto presenta attualmente una struttura molto articolata, con una gestione dei dati suddivisa in diverse cartelle di transito:

- `agent/`: Logica degli agenti e del sistema RAG.
- `pipeline/`: Script per l'acquisizione e il processamento iniziale dei dati.
- `knowledge_base/`: Manuali curati e tutorial (il "cuore" del RAG).
- `data/`: Cartella persistente (complicata):
    - `input/`: File grezzi caricati dall'utente o scaricati.
    - `output/`: File processati, puliti e pronti per l'indicizzazione.
    - `src/`: Codice sorgente ASM scaricato dagli scraper.
    - `tmp/`: File temporanei di download.
    - `vectorstore/`: Indice FAISS.
    - `models/`: Modelli GGUF e adapter LoRA.
- `utils/`: Utility per validazione, cycle counting e prompt management.

---

## 3. Flusso di Lavoro Standard

1. **Ingestion**: L'utente fornisce un URL o un file.
2. **Extraction**: Il sistema estrae il testo o il codice sorgente.
3. **Refinement**: Il testo viene pulito e convertito in Markdown con metadati.
4. **Indexing**: I nuovi file entrano nel database vettoriale FAISS.
5. **Reasoning**: L'utente pone una domanda; gli agenti recuperano le info e generano/validano il codice.

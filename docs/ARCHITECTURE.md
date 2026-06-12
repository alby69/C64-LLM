# Progetto C64 PDF-to-Dataset & Coding Agent

Questo progetto è un sistema end-to-end per la creazione di un assistente AI specializzato nella programmazione per Commodore 64 (Assembly 6502 e BASIC v2).

## Architettura del Sistema

L'architettura è suddivisa in tre macro-aree:

### 1. Data Pipeline (`pipeline/`)
Responsabile dell'acquisizione e trasformazione dei dati in un formato adatto all'addestramento.
- **pdf2text.py**: Estrae testo dai manuali PDF preservando il layout.
- **text_cleaner.py**: Pulisce il testo estratto, corregge errori comuni di OCR/estrazione e normalizza il codice.
- **c64_asm_scraper.py / clone_c64_asm.py**: Raccolgono codice sorgente reale da repository GitHub e siti web specializzati.
- **run_crawler.py**: Pipeline automatizzata per l'acquisizione proattiva di documentazione dalle fonti configurate in `config/crawler_sources.yaml` e trasformazione in note Obsidian.
- **build_dataset.py**: Analizza il testo e il codice sorgente per estrarre blocchi validi e generare coppie istruzione-output in formato JSONL.
- **train_lora.py**: Esegue il fine-tuning (LoRA) del modello base (Qwen2.5-Coder-1.5B) utilizzando il dataset generato.

### 2. Intelligent Agent (`agent/`)
Il sistema multi-agente e la logica di ragionamento.
- **orchestrator.py**: Il coordinatore centrale che gestisce il flusso di lavoro tra gli altri agenti e il self-healing.
- **researcher.py**: Espande le query dell'utente e recupera contesti tecnici dal Knowledge Engine.
- **crawler.py**: Agente proattivo per la ricerca e acquisizione di nuova conoscenza dal web, guidato dalla configurazione in `config/crawler_sources.yaml`.
- **coder.py**: Sintetizza codice C64 con personalità specializzate (BASIC/ASM) e ragionamento CoT.
- **validator.py**: Verifica la correttezza formale del codice generato (Assembly via ACME, BASIC via parser interno).
- **knowledge_base.py**: Il "Knowledge Engine". Supporta Wiki-links di Obsidian, parsing frontmatter e navigazione del grafo.
- **model_backend.py**: Astrazione del backend LLM. Supporta Transformers (GPU/4-bit) e LlamaCpp (CPU/GGUF).
- **agent_pro.py**: Punto di ingresso Gradio. Fornisce Prompt Library e visualizzazione del percorso di ricerca.

### 3. Validation Utils (`utils/`)
Strumenti per garantire la qualità del codice generato.
- **validate_emulator.py**: Interfaccia con l'assemblatore ACME e l'emulatore VICE per verificare che il codice assembly generato sia sintatticamente corretto e funzioni come previsto.

## Flusso dei Dati

1.  **Ingestione**: PDF e file ASM vengono caricati in `data/input/` e `data/src/`.
2.  **Processing**: La pipeline trasforma questi file in un dataset `dataset_unified.jsonl`.
3.  **Training**: Il modello viene addestrato con LoRA, producendo pesi ottimizzati in `data/models/`.
4.  **Inference**: L'utente interagisce con l'agente, che consulta il Knowledge Base e genera codice C64.

## Requisiti Hardware
Il sistema è ottimizzato per girare su macchine con **16GB di RAM**, utilizzando tecniche di quantizzazione a 4-bit per il modello LLM.

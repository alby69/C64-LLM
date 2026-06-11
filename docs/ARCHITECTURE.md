# Progetto C64 PDF-to-Dataset & Coding Agent

Questo progetto è un sistema end-to-end per la creazione di un assistente AI specializzato nella programmazione per Commodore 64 (Assembly 6502 e BASIC v2).

## Architettura del Sistema

L'architettura è suddivisa in tre macro-aree:

### 1. Data Pipeline (`pipeline/`)
Responsabile dell'acquisizione e trasformazione dei dati in un formato adatto all'addestramento.
- **pdf2text.py**: Estrae testo dai manuali PDF preservando il layout.
- **text_cleaner.py**: Pulisce il testo estratto, corregge errori comuni di OCR/estrazione e normalizza il codice.
- **c64_asm_scraper.py / clone_c64_asm.py**: Raccolgono codice sorgente reale da repository GitHub e siti web specializzati.
- **build_dataset.py**: Analizza il testo e il codice sorgente per estrarre blocchi validi e generare coppie istruzione-output in formato JSONL.
- **train_lora.py**: Esegue il fine-tuning (LoRA) del modello base (Qwen2.5-Coder-1.5B) utilizzando il dataset generato.

### 2. Intelligent Agent (`agent/`)
L'interfaccia utente e la logica di ragionamento.
- **knowledge_base.py**: Gestisce il RAG (Retrieval-Augmented Generation). Indicizza file Markdown in un database vettoriale FAISS.
- **agent_pro.py**: Il cuore dell'agente. Carica il modello quantizzato (4-bit) e integra i risultati del Knowledge Base nel prompt per fornire risposte precise. Utilizza Gradio per l'interfaccia chat.

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

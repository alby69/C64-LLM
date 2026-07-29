# C64-LLM

Assistente alla programmazione Commodore 64 avanzato con architettura multi-agente, RAG (Retrieval-Augmented Generation), validazione automatica (ACME + simulatore pure-Python py6502), knowledge distillation e integrazione nativa con Andrej Karpathy's nanoGPT come LLM locale predefinito.

Questo repository è il nucleo centrale del **C64 Intelligence Ecosystem**, progettato secondo un'architettura a plugin stile "Cheshire Cat AI" per orchestrare e consumare la conoscenza dei repository fratelli.

---

## Architettura dell'Ecosistema

Il sistema opera come un collettore integrato multi-repository:

```
    [C64-Scrapy] (Submodule) ────────┐
          │ (Crawling e Scraping)    │
          ▼                          ▼
    [C64-KB-Agent] (Submodule) ──→ [C64-LLM] (Questo Repo - Core Multi-Agente)
          │ (Standardizzazione KB)   │  ├─ Orchestrator (Self-healing Loop)
          └──────────────────────────┘  ├─ Researcher (RAG FAISS + HyDE)
                                        ├─ Coder (BASIC/Assembly Experts)
                                        ├─ Validator (Linter + py6502 + ACME)
                                        ├─ nanoGPT Engine (Default Backend Locale)
                                        └─ Interfaccia Gradio Pro (7 Tab + Wiki Graph)
```

---

## Integrazione Repository Fratelli (Submoduli)

C64-LLM include come **submoduli Git** i suoi progetti di supporto:
1. **`C64-KB-Agent`**: La singola fonte autoritativa di verità della conoscenza del C64. Contiene manuali digitalizzati, guide e Q&A pre-elaborati.
2. **`C64-Scrapy`**: Il motore di web scraping avanzato e mirato per acquisire manuali, sorgenti e documentazione tecnica da portali storici come Codebase64, Dustlayer e Archive.org.
3. **`external/py6502`**: Un fork/submodule del simulatore 6502 pure-Python `py65` integrato per eseguire analisi a tempo di esecuzione e validazioni di sicurezza del codice assembly generato.

---

## Componenti Core

### 1. Sistema Multi-Agente (`agent/`)
* **Orchestrator (`orchestrator.py`)**: Coordina il ciclo Researcher ➔ Coder ➔ Validator. Implementa logica di **auto-guarigione (self-healing)** multi-turno (default: 3 tentativi) re-iniettando i log di errore del linter o del simulatore direttamente nel prompt del Coder per correggere autonomamente bug di sintassi o logica.
* **Researcher (`researcher.py`)**: RAG specializzato su C64. Fornisce espansione automatica delle query, identificazione automatica del linguaggio target, ricerca semantica con FAISS e boosting dei pesi in base alla fonte (manuali curati > sorgenti > testi generici). Supporta opzionalmente HyDE (Hypothetical Document Embeddings).
* **Coder (`coder.py`)**: Genera codice Assembly 6502 o BASIC C64 utilizzando profili cognitivi ed esperti verticali, con logica Chain-of-Thought abilitata.
* **Validator (`validator.py` + `utils/`)**:
  - **BASIC Linter**: Controlla sequenza numeri di riga, collisione variabili (primi 2 caratteri significativi), cicli FOR/NEXT e range di indirizzi POKE.
  - **Assembly Branch**: Verifica la distanza dei salti condizionali (limite +/-127 byte) e si assicura che le routine terminino correttamente (RTS/JMP).
  - **ACME Assembler**: Lancia una validazione di cross-compilazione reale (se ACME è installato nel sistema).
  - **py6502 Simulator (`utils/py6502_utils.py`)**: Esegue un "dry run" sicuro del codice compilato per identificare crash, istruzioni non valide o loop infiniti prima di fornire il codice all'utente.
  - **Cycle Counter (`utils/cycle_counter.py`)**: Stima accuratamente i cicli di clock della CPU 6510 necessari per eseguire il blocco Assembly.

### 2. nanoGPT Integration Pipeline (`pipeline/`)
Il sistema adotta **nanoGPT** come backend locale predefinito per superare i limiti di conoscenza sintattica dei modelli generalisti sul codice retrò:
* **nanoGPT Prepper (`nanogpt_prepper.py`)**: Raccoglie la documentazione da `C64-KB-Agent`, i sorgenti di esempio e le Q&A distillate, compilando un corpus di addestramento massivo (~50M caratteri). Supporta tre tokenizzazioni: character-level, GPT-2 BPE (via `tiktoken`) e un BPE addestrato su misura sul vocabolario C64 (`c64_custom`).
* **nanoGPT Trainer (`nanogpt_trainer.py`)**: Wrapper per clonare, configurare ed eseguire l'addestramento (pre-training da zero o fine-tuning di pesi GPT-2) monitorando la curva di loss.
* **Modelli nanoGPT locale (`agent/model_backend.py`)**: La classe `NanoGPTBackend` carica direttamente i checkpoint `.pt` addestrati per l'inferenza ad altissima velocità (10-20 tok/s su CPU).

---

## Interfaccia Gradio UI (`agent/agent_pro.py`)

Avvia l'interfaccia Gradio Pro completa con 7 Tab interattivi:
```bash
python -m agent.agent_pro
```

1. **Chat**: Chat multi-turno con selettore di modalità (Base, RAG, LoRA, RAG+LoRA), nuvola di 160+ termini C64 cliccabili, log asincroni dell'esecuzione degli agenti e cursore per i tentativi di self-healing.
2. **Download e Siti**: Download intelligente di file `.pdf`, `.d64`, `.prg`, `.g64`. Rileva ed delega automaticamente il crawling di URL di Archive.org o Google Drive a **C64-Scrapy**, re-indirizzando l'utente alla scheda di sincronizzazione.
3. **Integrazione C64-KB-Agent**: Consente di monitorare i submoduli, lanciare gli spider Scrapy in tempo reale e sincronizzare i documenti md puliti con l'adattatore `ScrapyKBAdapter`.
4. **Knowledge Base**: Esplora i documenti indicizzati, visualizza la copertura del RAG e ricostruisce/re-indicizza il vector store FAISS.
5. **Distillazione e LoRA**: Genera dataset sintetici Q&A (factual, theory, codegen, explain, bugfix) usando 5 possibili backend Teacher (Groq, OpenRouter, OpenCode, ecc.) ed esegue il LoRA training locale.
6. **nanoGPT**: Gestisce interamente la pipeline nanoGPT. Permette di preparare il corpus, scegliere la tokenizzazione, impostare i parametri del modello (124M/350M), avviare/fermare in modo asincrono l'addestramento visualizzando la loss in streaming e convertire i checkpoint in GGUF.
7. **Dati**: Esploratore tabellare del dataset generato o distillato.
8. **Retro Editor & Linter**: Editor di codice Monaco C64 retro-styled con evidenziazione sintattica avanzata e linter statico in tempo reale. Offre auto-fix autonomo di errori sintattici tramite agenti (Self-Healing).
9. **Emulatore VICE**: Emulatore grafico C64 HTML5/Canvas integrato con pannello interattivo per la visualizzazione dello stato dei registri CPU 6510 e download del file `.prg` compilato.
10. **Galleria Asset Visivi**: Visualizzazione e ricerca degli sprite, charset e bitmap decodificati. Consente l'esportazione automatica di codice pronto da eseguire nel C64.
11. **Mappa Memoria**: Rappresentazione grafica interattiva della memoria del C64 con hover informativo, raccomandazioni per codice macchina e controllo di sicurezza anti-collisione per i range di indirizzi.
* **Wiki Graph (Mappa Concettuale)**: Grafo concettuale C64 interattivo in SVG integrato nella UI con 87 nodi e 105 archi, con zoom, pan e filtri.

---

## Installazione Rapida

Assicurarsi che i submoduli siano aggiornati:
```bash
git submodule update --init --recursive
```

Installare le dipendenze:
```bash
pip install -r requirements.txt
```

Avviare la UI:
```bash
PYTHONPATH=. python3 agent/agent_pro.py
```

### Esecuzione con Docker Compose
```bash
docker compose up c64-ui              # Avvia Gradio su http://localhost:7860
docker compose run c64-pipeline       # Avvia la pipeline di indicizzazione RAG
docker compose up c64-train           # Avvia il training LoRA
```

---

## Test di Integrità e Validazione
Il repository dispone di un'ampia suite di test per validare gli agenti, il RAG, la pipeline nanoGPT e l'integrazione con py6502.
Esegui tutti i test con:
```bash
PYTHONPATH=. pytest
```

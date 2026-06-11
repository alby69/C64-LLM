# C64 Multi-Agent Coding Assistant

Questo progetto è un assistente alla programmazione specializzato per il **Commodore 64**, capace di generare codice **Assembly 6502** e **BASIC v2**. Utilizza un'architettura multi-agente avanzata e un sistema RAG (Retrieval-Augmented Generation) per garantire precisione tecnica e ridurre le allucinazioni.

## 🚀 Caratteristiche Principali

- **Architettura Multi-Agente**:
    - **ResearcherAgent**: Espande le query dell'utente e recupera informazioni tecniche dal Knowledge Base.
    - **CoderAgent**: Genera codice con 'personalità' specifiche (BASIC/Assembly) e ragionamento strutturato.
    - **ValidatorAgent**: Verifica il codice tramite l'assembler ACME e un parser BASIC v2 dedicato.
    - **OrchestratorAgent**: Coordina il flusso e gestisce il self-healing.
- **C64 Knowledge Engine**: Un sistema RAG avanzato che integra un **Vault Obsidian**, supporta Wiki-links per la navigazione del grafo di conoscenza e parsing dei metadati (frontmatter).
- **Prompt Management System (PMS)**: Centralizza tutti i prompt in file YAML gestiti via `PromptManager` per un disaccoppiamento totale tra logica e istruzioni.
- **Ottimizzazione Locale (CPU Only)**: Supporto per modelli **GGUF** tramite `llama.cpp`, ideale per girare su macchine con 16GB RAM senza GPU.

## 📂 Struttura del Progetto

- `agent/`: Logica degli agenti e del sistema RAG.
- `docs/`: Documentazione approfondita sull'architettura e sul design degli agenti.
- `pipeline/`: Script per la preparazione del dataset (PDF to Text, Cleaning).
- `utils/`: Strumenti di validazione e interazione con l'emulatore.
- `knowledge_base/`: Documentazione tecnica in formato Markdown.
- `data/`: Memoria vettoriale e output della pipeline.

## 🛠️ Installazione e Utilizzo

### Requisiti
- Python 3.10+
- [ACME Assembler](https://github.com/meonwax/acme) (per la validazione del codice)
- [VICE Emulator](http://vice-emu.sourceforge.net/) (opzionale, per testare i file .prg)

### Setup
```bash
pip install -r requirements.txt
```

### Avvio dell'Interfaccia PRO (Gradio)
```bash
python -m agent.agent_pro
```

## 📖 Documentazione
Per maggiori dettagli, consulta la cartella `docs/`:
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): Panoramica del sistema.
- [REFACTORING.md](docs/REFACTORING.md): Dettagli sulla transizione al sistema multi-agente.
- [RESEARCHER_DEEP_DIVE.md](docs/RESEARCHER_DEEP_DIVE.md): Funzionamento del Researcher.
- [CODER_DEEP_DIVE.md](docs/CODER_DEEP_DIVE.md): Strategie di generazione del Coder.

---
*Progetto sviluppato per preservare e potenziare l'arte della programmazione su sistemi 8-bit.*

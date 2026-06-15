# C64 Multi-Agent Coding Assistant

Questo progetto è un assistente alla programmazione specializzato per il **Commodore 64**, capace di generare codice **Assembly 6502** e **BASIC v2**. Utilizza un'architettura multi-agente avanzata e un sistema RAG (Retrieval-Augmented Generation).

## 🚀 Caratteristiche Principali

- **Architettura Multi-Agente**: Researcher, Coder, Validator, e Orchestrator lavorano insieme con meccanismo di **Self-Healing**.
- **C64 Knowledge Engine**: Sistema RAG avanzato con supporto **HyDE** e Wiki-links Obsidian.
- **Performance Aware**: Include un **Cycle Counter** per Assembly e validazione sintattica rigorosa per BASIC v2.
- **Configurabile & Estensibile**: Gestione tramite `agent_config.yaml` e Prompt Management System (PMS).

## 📂 Struttura del Progetto

- `agent/`: Logica degli agenti e del sistema RAG.
- `docs/`: Documentazione tecnica consolidata.
- `pipeline/`: Script per la preparazione del dataset e crawling proattivo.
- `utils/`: Strumenti di validazione, cycle counting e utility.
- `config/`: Configurazioni di sistema e sorgenti.
- `prompts/`: Repository centrale dei prompt.

## 🛠️ Installazione e Utilizzo

### Requisiti
- Python 3.10+
- [ACME Assembler](https://github.com/meonwax/acme) (per la validazione del codice)

### Setup
```bash
pip install -r requirements.txt
```

### Avvio dell'Interfaccia PRO (Gradio)
```bash
python -m agent.agent_pro
```

## 📖 Documentazione
- [TECHNICAL_MANUAL.md](docs/TECHNICAL_MANUAL.md): **Manuale Tecnico Completo.** Architettura, agenti, RAG e roadmap.

---
*Progetto sviluppato per preservare e potenziare l'arte della programmazione su sistemi 8-bit.*

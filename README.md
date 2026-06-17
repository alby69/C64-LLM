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
- ACME Assembler (per la validazione del codice, già installato nell'immagine Docker)
  - Su host: `apt install acme` (Debian/Ubuntu) o `brew install acme` (macOS)

### Setup
```bash
pip install -r requirements.txt
```

### Avvio dell'Interfaccia PRO (Gradio)
```bash
python -m agent.agent_pro
```

## 🐳 Docker Quickstart

### Prerequisiti
- Docker e Docker Compose installati
- **Su CPU**: scarica un modello GGUF (obbligatorio, vedi sotto)
- GPU NVIDIA con [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/) (opzionale)

### Setup modello (CPU)
Su CPU serve un modello in formato GGUF:
```bash
# Crea la cartella e scarica il modello
mkdir -p data/models
wget -O data/models/qwen2.5-coder-1.5b.Q4_K_M.gguf https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
```
Il `docker-compose.yml` punta già a questo percorso con `GGUF_MODEL_PATH`.

### Build dell'immagine
```bash
docker compose build
```

### Avvio interfaccia Gradio (UI)
```bash
docker compose up c64-ui
```
L'interfaccia sarà disponibile su [http://localhost:7860](http://localhost:7860).

### Pipeline dati (estrazione PDF → pulizia → dataset)
```bash
# Metti i tuoi PDF in ./data/input/
mkdir -p data/input data/output

# Esegui l'intera pipeline (PDF → dataset)
docker compose run c64-pipeline

# Oppure imposta manualmente il PDF da processare
INPUT_PDF=mio_documento.pdf docker compose up c64-pipeline
```

### Training LoRA
```bash
docker compose up c64-train
```
Il modello addestrato verrà salvato in `./data/models/c64-lora-pro/`.

#### Note per CPU:
- Il training rileva automaticamente la CPU e usa il modello `Qwen/Qwen2.5-Coder-0.5B-Instruct`
- `max_length=512`, `batch_size=1`, `gradient_accumulation_steps=2`
- Evaluation e salvataggio checkpoint disabilitati per velocità
- Gradient clipping (`max_grad_norm=1.0`) e learning rate ridotto (`1e-4`) per stabilità
- Default UI: `Max sequence length` = 512 (regolabile fino a 4096 per GPU)

### Altri comandi utili
```bash
# Estrarre testo da un PDF specifico
docker compose run c64-pipeline python pipeline/pdf2text.py /app/data/input/manuale.pdf /app/data/output/raw.txt

# Pulire il testo estratto
docker compose run c64-pipeline python pipeline/text_cleaner.py /app/data/output/raw.txt /app/data/output/clean.txt

# Generare dataset
docker compose run c64-pipeline python pipeline/build_dataset.py /app/data /app/data/output/dataset_unified.jsonl

# Costruire l'indice vettoriale (Knowledge Base)
docker compose run c64-pipeline python agent/knowledge_base.py

# Estrarre BASIC/ML da un disco D64
docker compose run c64-pipeline python pipeline/extract_d64.py /app/data/input/disk.d64 /app/data/output/

# Estrarre BASIC/ML da un disco G64
docker compose run c64-pipeline python pipeline/extract_g64.py /app/data/input/disk.g64 /app/data/output/

# Estrarre BASIC/ML da un file PRG
docker compose run c64-pipeline python pipeline/extract_prg.py /app/data/input/program.prg /app/data/output/

# Eseguire i test
docker compose run c64-pipeline python -m pytest tests/ -v
```

### Volume dati
Tutti i dati persistenti (PDF, output, modelli) sono in `./data/`, montato come volume in `/app/data` nel container.

## 📚 Popolare la Knowledge Base (RAG)

La Knowledge Base alimenta il sistema RAG con documentazione tecnica C64.

### Workflow rapido (minimo indispensabile)

```bash
# 1. Scarica documentazione Assembly da siti C64
docker compose run --rm c64-pipeline python pipeline/c64_asm_scraper.py --sites 6502org codebase64 c64wiki --delay 1.5

# 2. Ricostruisci l'indice vettoriale
docker compose run --rm c64-pipeline python agent/knowledge_base.py

# 3. Riavvia l'UI
docker compose restart c64-ui
```

### Alternative per aggiungere dati

- **PDF**: metti i file in `./data/input/`, poi esegui `docker compose run c64-pipeline`
- **Dischi D64**: metti i file in `./data/input/`, poi esegui `docker compose run c64-pipeline python pipeline/extract_d64.py /app/data/input/disk.d64 /app/data/input/`
- **Dischi G64**: metti i file in `./data/input/`, poi esegui `docker compose run c64-pipeline python pipeline/extract_g64.py /app/data/input/disk.g64 /app/data/input/`
- **PRG**: metti i file in `./data/input/`, poi esegui `docker compose run c64-pipeline python pipeline/extract_prg.py /app/data/input/program.prg /app/data/input/`
- **Archive.org (UI)**: inserisci l'URL dell'item (es. `https://archive.org/details/c64-programmer-ref`).
  Il sistema seleziona automaticamente il miglior formato disponibile (TXT > EPUB > HTML > PDF) e scarica un solo file.
- **Markdown manuali**: crea file `.md` in `./knowledge_base/` con frontmatter YAML:
  ```markdown
  ---
  title: "Nome Documento"
  tags: [c64, assembly]
  ---
  Contenuto...
  ```

**Nota importante**: I file `.txt` in `data/output/` (estrazioni OCR da PDF) NON vengono più inclusi nell'indice FAISS — contenevano artefatti OCR che causavano allucinazioni. Solo i file `.md` curati in `knowledge_base/` vengono indicizzati.

## 🧠 Knowledge Distillation

Il progetto include un sistema di **Teacher→Student distillation** per specializzare Qwen2.5-Coder-1.5B su C64.

### Flusso

```
Teacher LLM (OpenCode / Groq / OpenRouter / Ollama)
       │  Legge la Knowledge Base
       │  Genera QA sintetiche (factual, code, explain, bugfix, theory)
       ▼
Dataset distillato (data/output/distill_dataset.jsonl)
       │
       ▼
LoRA Fine-tuning → Qwen specializzato (data/models/c64-lora-pro/)
```

### Teacher predefinito: OpenCode (gratuito)

Nessuna API key. L'assistente OpenCode legge la KB e genera il dataset. Sono già state generate **76 QA pairs** che coprono tutti i 10 file KB.

### Altri backend Teacher

| Backend | Comando |
|---------|---------|
| **Groq** (gratuito) | `python pipeline/knowledge_distiller.py --teacher groq --generate` |
| **OpenRouter** | `python pipeline/knowledge_distiller.py --teacher openrouter --model qwen/qwen3-32b --generate` |
| **Ollama** | `python pipeline/knowledge_distiller.py --teacher ollama --model qwen3:32b --generate` |

### Addestramento

```bash
python pipeline/train_lora.py data/output/distill_dataset.jsonl
```

### UI

Il tab **Distillazione** nell'interfaccia Gradio permette di:
- Selezionare backend, modello, tipi di dato e lingue
- Generare il dataset con un click
- Addestrare Qwen via LoRA
- Monitorare lo stato

### Documenti correlati
- [docs/PIANO_DISTILLAZIONE.md](docs/PIANO_DISTILLAZIONE.md) — Piano dettagliato
- [docs/FONTI_DELLA_CONOSCENZA.md](docs/FONTI_DELLA_CONOSCENZA.md) — Cosa usa Qwen per rispondere
- [docs/TECHNICAL_MANUAL.md](docs/TECHNICAL_MANUAL.md) — Manuale tecnico completo

## 📖 Documentazione
- [TECHNICAL_MANUAL.md](docs/TECHNICAL_MANUAL.md): **Manuale Tecnico Completo.** Architettura, agenti, RAG e roadmap.
- [UI_MANUAL.md](docs/UI_MANUAL.md): **Manuale dell'Interfaccia Utente.** Descrizione di tutti i tab e controlli.
- [FONTI_DELLA_CONOSCENZA.md](docs/FONTI_DELLA_CONOSCENZA.md): **Fonti usate da Qwen.** KB, prompt, flusso RAG.
- [PIANO_DISTILLAZIONE.md](docs/PIANO_DISTILLAZIONE.md): **Piano di Knowledge Distillation.** Teacher→Student, dataset, training.

---
*Progetto sviluppato per preservare e potenziare l'arte della programmazione su sistemi 8-bit.*

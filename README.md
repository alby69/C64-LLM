📚 C64 PDF-to-Dataset Pipeline – Advanced Documentation

Benvenuto nel repository C64 PDF-to-Dataset, una pipeline completa e modulare per trasformare libri di programmazione in Assembly per Commodore 64 in dataset pronti per addestramento LoRA ottimizzati per 6502.

Questa documentazione avanzata guida l'utente passo passo, includendo flussi, suggerimenti per ottimizzazione, e strumenti di validazione.

🧩 Pipeline Overview

La pipeline completa è strutturata in fasi modulari:

PDF/ASM input
   │
   ▼
[1] pdf2text.py o lettura diretta ASM
   │
   ▼
Raw Text (.txt)
   │
   ▼
[2] text_cleaner.py
   │
   ▼
Clean Text (.txt)
   │
   ▼
[3] build_dataset.py
   │
   ▼
Dataset JSONL (.jsonl)
   │
   ├─────────────► [4] train_lora.py ──► LoRA 6502 Model
   │
   └─────────────► [5] validate_emulator.py ──► Validation Report

⚙️ Requisiti
Python ≥ 3.10
Pacchetti Python:
pip install -r requirements.txt
GPU consigliata per training LoRA, ma compatibile anche CPU
Emulator C64 opzionale per validazione (ACME assembler + VICE)

Per gli scraper (c64_asm_scraper.py e clone_c64_asm.py):
pip install requests beautifulsoup4 lxml
git installato nel sistema

🐳 Docker

La pipeline può essere eseguita completamente in container Docker.

📦 Prerequisiti

- Docker >= 20.10
- docker-compose >= 1.29

🏗️ Build dell'immagine

```bash
docker build -t c64-llm .
```

🚀 Quick Start

```bash
# Clona repo GitHub con codice C64/6502
python clone_c64_asm.py --output ./data/src

# Scarica codice da siti web (opzionale)
python c64_asm_scraper.py

# Esegui l'intera pipeline (PDF + ASM)
docker-compose up --build
```

Questo esegue automaticamente:
1. Estrazione PDF → testo (se presente)
2. Lettura file ASM da src/ (se presente)
3. Pulizia testo
4. Generazione dataset JSONL

📂 Struttura Dati

```
data/
├── input/              # PDF sorgente (.pdf) + file scaricati dagli scraper
├── src/                # File assembly (.asm) + repo clondati
│   ├── algorithms/
│   ├── examples/
│   ├── games/
│   └── include/
├── output/             # File intermedi + dataset
│   ├── raw.txt
│   ├── clean.txt
│   └── dataset.jsonl
└── models/             # Modelli addestrati
```

🔧 Tipo di Input

Puoi scegliere quale tipo di file processare con la variabile `INPUT_TYPE`:

```bash
# Solo file ASM
INPUT_TYPE=asm docker-compose up c64-pipeline

# Solo file PDF
INPUT_TYPE=pdf docker-compose up c64-pipeline

# Tutti e due (PDF + ASM)
INPUT_TYPE=all docker-compose up c64-pipeline
```

Il default è `asm` se non specificato.

Comando diretto:
```bash
# Solo ASM
python build_dataset.py asm /data /data/output/dataset.jsonl

# Solo PDF
python build_dataset.py pdf /data /data/output/dataset.jsonl

# Tutti e due
python build_dataset.py all /data /data/output/dataset.jsonl
```

📦 Script Principali

| Script | Descrizione |
|--------|-------------|
| `pdf2text.py` | Estrae testo da PDF |
| `text_cleaner.py` | Pulisce e normalizza il testo |
| `build_dataset.py` | Genera dataset JSONL da PDF e/o ASM |
| `train_lora.py` | Addestra modello LoRA (richiede GPU) |
| `validate_emulator.py` | Valida codice su emulatore C64 |
| `c64_asm_scraper.py` | Scarica codice ASM da siti web (6502.org, Codebase64, GitHub, ecc.) |
| `clone_c64_asm.py` | Clona repo GitHub con codice C64/6502 |

🐚 Comandi Docker Manuali

# PDF → testo
docker run -v $(pwd)/data:/data c64-llm python pdf2text.py /data/input/libro.pdf /data/output/raw.txt

# Pulizia testo
docker run -v $(pwd)/data:/data c64-llm python text_cleaner.py /data/output/raw.txt /data/output/clean.txt

# Generazione dataset (tutti i tipi)
docker run -v $(pwd)/data:/data c64-llm python build_dataset.py all /data /data/output/dataset.jsonl

# Training LoRA (CPU - lento!)
docker run -v $(pwd)/data:/data c64-llm python train_lora.py /data/output/dataset.jsonl

🐚 Comandi Docker Compose

# Solo pipeline → Dataset
docker-compose up c64-pipeline

# Solo training
docker-compose up c64-train

# Entrambi
docker-compose up

# Rebuild
docker-compose build --no-cache

🔧 Variabili Ambiente

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - INPUT_TYPE=all  # pdf, asm, o all
  - CUDA_VISIBLE_DEVICES=""  # per CPU only
```

⚠️ Note per CPU-only

Il training su CPU è molto lento. Parametri ottimizzati:
- max_steps: 100 (vs 1500 GPU)
- r: 16 (vs 32 GPU)
- batch_size: 1

Per risultati migliori, usa una GPU NVIDIA con CUDA.

📂 Struttura Repository
c64-pdf-dataset/
├─ data/                    # Dati input/output
├─ *.py                    # Script pipeline
│  ├─ pdf2text.py          # Estrazione PDF
│  ├─ text_cleaner.py      # Pulizia testo
│  ├─ build_dataset.py     # Generazione dataset
│  ├─ train_lora.py        # Training LoRA
│  ├─ validate_emulator.py # Validazione emulator
│  ├─ c64_asm_scraper.py   # Scraper siti web
│  └─ clone_c64_asm.py     # Clona repo GitHub
├─ clone_c64_asm.sh        # Script shell originale (legacy)
├─ Dockerfile              # Container Docker
├─ docker-compose.yml      # Orchestrazione
└─ requirements.txt        # Dipendenze

🔧 Suggerimenti Avanzati

Dataset Management
Mantieni sempre una copia raw del PDF per confronto.
Genera versioni multiple di dataset per esperimenti differenti.
Combina PDF e file ASM per un dataset più completo.

Acquisizione Dati
```bash
# Clona repo GitHub con codice C64/6502
python clone_c64_asm.py --output ./data/src

# Scarica codice da siti web
python c64_asm_scraper.py --sites codebase64 6502org

# Scarica tutto
python c64_asm_scraper.py
```

I file scaricati vengono organizzati automaticamente:
- `data/src/[nome_sito]/` per file ASM
- `data/input/[nome_sito]/` per PDF

Training Tips
Per più libri, concatena i dataset .jsonl o usa dataset.load_dataset di Hugging Face.
Testa il modello su esempi reali di codice prima della validazione finale.
Per addestramento rapido, usa solo campioni "hardcore" selezionati.

Validazione e Debug
Usa il report dell'emulatore per identificare pattern di codice che causano crash.
Puoi estrarre solo subroutine specifiche per debug isolati.

📈 Roadmap / Prossimi Step

Integrazione diretta con Hugging Face transformers per deploy modelli LoRA.
Supporto multi-lingua per libri di programmazione diversi da inglese.
GUI web per pipeline drag-and-drop dei PDF.
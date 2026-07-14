# Manuale Tecnico C64-LLM

## 1. Architettura Multi-Agente

```
Utente → Orchestrator → Researcher (RAG) → Coder → Validator → Risposta
                             ↑_________________________| (self-healing loop, max 3)
```

### Orchestrator (`agent/orchestrator.py`)
Ciclo: Researcher recupera contesto RAG → Coder genera codice → Validator controlla. Se fallisce, riprova fino a 3 passando i log errore al Coder.

### Researcher (`agent/researcher.py`)
- Query expansion via LLM
- Language detection (BASIC vs Assembly)
- FAISS retrieval: k=10, chunk_size=2000, overlap=200
- Source boosting: knowledge_base 3x, data/src 2x, docs 1.5x
- HyDE (Hypothetical Embeddings) disabilitato — peggiora retrieval su modelli piccoli

### Coder (`agent/coder.py`)
- Genera codice con profili BASIC Expert / Assembly Expert
- Chain-of-Thought: pianificazione logica prima del codice
- Prompt system da `prompts/prompts.yaml` con regole anti-allucinazione

### Validator (`agent/validator.py`)
| Controllo | Cosa fa |
|-----------|---------|
| BASIC Linter | linee sequenziali, variabili (primi 2 char), FOR/NEXT, POKE range |
| Assembly Branch | branch +/-127 byte, routine terminano con RTS/JMP |
| ACME | cross-assemblatore reale |
| py6502 | simulazione dry-run, rileva loop infiniti, istruzioni illegali |
| Cycle Counter | stima cicli di clock per routine Assembly |

## 2. RAG Engine (`agent/knowledge_base.py`)

### Indicizzazione
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (384 dim)
- Vector store: FAISS diretto
- Chunk: RecursiveCharacterTextSplitter(2000, 200)
- Filtri: keyword C64 ≥ 15, > 1KB, skip binari (gz,zip,png,pdf,d64)
- Falsi `.asm` esclusi (doppia estensione > 500KB)
- Marker-pdf `.md` → boost 1.2; `_clean.txt` → boost 0.3

### Fonti indicizzate
| Path | Contenuto |
|------|-----------|
| `knowledge_base/*.md` | 9 manuali curati |
| `data/input/*.bas.txt` | BASIC detokenizzato |
| `data/input/*.ml.txt` | machine language estratto |
| `data/src/*.asm` | Assembly scrapato |
| `data/output/*_clean.txt` | PDF puliti (filtrati) |
| `docs/*.md` | documentazione progetto |

## 3. Data Pipeline

### Estrazione
| Script | Input | Output |
|--------|-------|--------|
| `extract_d64.py` | D64 | `*.bas.txt` BASIC detokenizzato |
| `extract_g64.py` | G64 | GCR decode → `*.bas.txt` + `*.ml.txt` |
| `extract_prg.py` | PRG | BASIC (detokenize) o ML (hex dump) |
| `pdf2marker.py` | PDF | `.md` + `.txt` + `.meta.json` (via marker-pdf) o solo `.txt` (PyMuPDF fallback) |
| `text_cleaner.py` | TXT | OCR artifact cleanup |

### Build dataset
- `build_dataset.py` → `data/output/dataset_unified.jsonl`
- Rileva blocchi BASIC/Assembly, genera coppie instruction/context/output

### nanoGPT Prepper (`pipeline/nanogpt_prepper.py`)
- Corpus C64 da KB + sorgenti + Q&A distillate
- Tokenizzazione char-level o BPE (GPT-2 via tiktoken)
- Output: `train.bin`, `val.bin`, `meta.pkl`
- Pronto per karpathy/nanoGPT

## 4. Knowledge Distillation

### Teacher → Student
```
KnowledgeBase → Teacher LLM → dataset sintetico JSONL → LoRA fine-tuning → Qwen specializzato
```

### 5 tipi di dato
factual, codegen, explain, bugfix, theory — in italiano o inglese

### Teacher backends
| Backend | API Key | Costo |
|---------|---------|-------|
| opencode | No | 0 |
| Groq | Sì (gratuita) | 0 |
| OpenRouter | Sì | ~$1-3 |
| Ollama | No | 0 (locale) |
| HuggingFace | Sì | 0 (free tier) |

### LoRA Training (`pipeline/train_lora.py`)
| Parametro | CPU | GPU |
|-----------|-----|-----|
| Modello | Qwen 0.5B | Qwen 1.5B |
| Max length | 512 | 2048 |
| Batch | 1, accum 2 | 2, accum 4 |
| LR | 1e-4 | 2e-4 |
| Eval | disabilitato | ogni 20 step |

## 5. Backend Modello (`agent/model_backend.py`)

Due backend configurabili:
- **LlamaCppBackend** (default se GGUF presente) — `n_ctx=8192`, `n_threads=os.cpu_count()`
- **ModelBackend** (HF Transformers) — 4-bit quantization, LoRA dinamico via PeftModel

## 6. Configurazione

`config/agent_config.yaml`:
- `agent.max_attempts`: default 3
- `rag.k`: 10, `use_hyde`: false, `chunk_size`: 2000, `overlap`: 200
- `model`: Qwen/Qwen2.5-Coder-1.5B-Instruct, temperature 0.3

## 7. UI (agent/agent_pro.py)

### Tab Chat
- Modalità: Base / RAG(default) / LoRA / RAG+LoRA
- Technical Terms cloud: 160+ termini C64 cliccabili
- Auto-elabora link: estrae URL da chat → pipeline automatica
- Self-healing slider: 1-5 tentativi

### Tab Scarica e Siti
Download + scraping integrato: URL singoli, Archive.org, Google Drive

### Tab Knowledge Base
Ricostruzione indice FAISS, esplora file, anteprima

### Tab Distillazione
Profili di configurazione, genera dataset, addestra LoRA

### Tab Dati
Dataset viewer con paginazione e ricerca

### Wiki Graph
Grafo concettuale SVG: 87 nodi, 105 archi, 7 gruppi collassabili, zoom/pan

## 8. Integrazione con ecosistema

### C64-Scrapy (acquisizione)
`pipeline/acquisition/scrapy_kb_adapter.py`:
- `sync()` — copia file Markdown da C64-KB-Agent con verifica MD5
- `run_scrapy_spider()` — lancia spider C64-Scrapy con auto-sync

### PYC64 (tools)
`examples/plugins/pyc64_integration.py` — esempio di integrazione

## 9. Docker

| Servizio | Comando | Porta |
|----------|---------|-------|
| UI | `docker compose up c64-ui` | 7860 |
| Pipeline | `docker compose run c64-pipeline` | — |
| Training | `docker compose up c64-train` | — |

Volumi: `./data/` → `/app/data`, `./knowledge_base/` → `/app/knowledge_base/`

## 10. Test

```
python -m pytest tests/ -v
```

# C64-LLM

Assistente alla programmazione C64 con architettura multi-agente, RAG, validazione automatica e knowledge distillation.

## Architettura

```
 C64-Scrapy ──→ C64-KB-Agent ──→ C64-LLM (questo repo)
 (scraping)      (standardizza)    │
                                   ├─ Orchestrator (auto-guarigione)
                                   │   ├─ Researcher (RAG FAISS)
                                   │   ├─ Coder (BASIC/Assembly)
                                   │   └─ Validator (ACME + py6502)
                                   ├─ Knowledge Distillation
                                   ├─ nanoGPT prepper
                                   └─ Interfaccia Gradio
```

## Componenti Core

| Componente | File | Ruolo |
|-----------|------|-------|
| Orchestrator | `agent/orchestrator.py` | Ciclo Researcher→Coder→Validator con self-healing (fino a 3 tentativi) |
| Researcher | `agent/researcher.py` | Espansione query, retrieval FAISS, HyDE (disabilitato di default) |
| Coder | `agent/coder.py` | Generazione codice con profili BASIC/Assembly |
| Validator | `agent/validator.py` | Linter BASIC, branch range, ACME, py6502 simulazione, cycle counting |
| RAG | `agent/knowledge_base.py` | FAISS + sentence-transformers, chunk 2000/200, filtri PDF |
| Distiller | `pipeline/knowledge_distiller.py` | 5 teacher backends (OpenCode, Groq, OpenRouter, Ollama, HuggingFace) |
| LoRA Trainer | `pipeline/train_lora.py` | LoRA su Qwen con auto CPU/GPU detection |
| nanoGPT Prepper | `pipeline/nanogpt_prepper.py` | Corpus C64 + tokenizzazione char/BPE → train.bin/val.bin |
| UI | `agent/agent_pro.py` | Gradio 5 tab (Chat, Download, KB, Distill, Dati + Wiki Graph) |

## Quickstart

```bash
pip install -r requirements.txt
python -m agent.agent_pro
```

### Versioni lunghe

- `python pipeline/extract_d64.py <file.d64> <output/>` — estrae BASIC da dischi
- `python pipeline/extract_prg.py <file.prg> <output/>` — estrae BASIC/ML da PRG
- `python pipeline/pdf2marker.py <input.pdf> <output/>` — PDF → Markdown
- `python pipeline/build_dataset.py <data/dir> <output.jsonl>` — dataset Q/A
- `python pipeline/train_lora.py <dataset.jsonl>` — LoRA fine-tuning
- `python pipeline/nanogpt_prepper.py char` — prepara corpus per nanoGPT

## Docker

```bash
docker compose build
docker compose up c64-ui              # Gradio su :7860
docker compose run c64-pipeline       # pipeline dati
docker compose up c64-train           # LoRA training
```

Il modello GGUF va in `data/models/`. Default: Qwen 2.5 Coder 1.5B.

## Riferimenti esterni

Questo progetto è parte dell'ecosistema [C64-Intelligence-SDK](https://github.com/alby69/C64-Intelligence-SDK) e si integra con:
- **C64-Scrapy** — motore di scraping web specializzato
- **C64-KB-Agent** — knowledge base standardizzata
- **PYC64** — utility Python per C64 (dischi, PRG, disassemblamento)

## Struttura directory

```
agent/           agente multi-agente + RAG
pipeline/        data pipeline (estrazione, pulizia, training)
utils/           utility (cycle counter, prompt manager, py6502)
config/          configurazioni YAML
prompts/         repository prompt templates
knowledge_base/  manuali C64 curati (9 file MD)
data/
  models/        GGUF + LoRA adapter
  vectorstore/   indice FAISS
  output/        PDF estratti + dataset
  src/           sorgenti scartati
  input/         file grezzi caricati
```

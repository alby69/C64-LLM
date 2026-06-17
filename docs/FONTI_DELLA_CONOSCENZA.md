# Fonti della Conoscenza — Cosa usa Qwen per rispondere in chat

> Quali file e componenti intervengono quando fai una domanda nella chat e Qwen genera una risposta.

---

## 1. Knowledge Base (contesto RAG)

Quando la RAG è attiva, il sistema cerca i chunk più rilevanti in un indice FAISS costruito a partire da questi file:

| Directory | Contenuto | Quanti |
|-----------|-----------|--------|
| `knowledge_base/*.md` | Manuali scritti a mano: memory map, VIC-II, SID, sprite, raster, KERNAL, BASIC tutorial, indirizzamenti 6502, routine schermo, CIA | 9 file |
| `data/output/*_clean.txt` | Libri tecnici puliti (C64 Programmer's Reference Guide, Mapping the C64, 6502 Assembly Language, ecc.) | 76+ file |
| `data/input/*.bas.txt` | Programmi BASIC v2 estratti da D64/G64/PRG | vari |
| `data/input/*.ml.txt` | Codice machine language estratto | vari |
| `data/src/*.asm` | Assembly 6502 scaricato da siti (Codebase64, 6502.org, ecc.) | vari |
| `docs/*.md` | Documentazione interna del progetto | 6 file |

### Come viene costruito l'indice

```
knowledge_base.py (C64KnowledgeBase.build_index())
  → sentence-transformers/all-MiniLM-L6-v2 (embedding)
  → RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
  → FAISS vector store salvato in data/vectorstore/
```

---

## 2. Prompt Templates (istruzioni per Qwen)

Tutti in `prompts/prompts.yaml`:

| Prompt | Usato da | Scopo |
|--------|----------|-------|
| `coder.base.system` | CoderAgent | Istruzione principale: come scrivere codice C64, sintassi BASIC/Assembly, divieto di allucinare comandi inesistenti |
| `researcher.expansion.system` | ResearcherAgent | Espandere la query utente in termini tecnici |
| `researcher.language_detection.system` | ResearcherAgent | Rilevare se la richiesta è BASIC o Assembly |
| `orchestrator.self_healing.user_template` | OrchestratorAgent | Template per il ciclo di self-healing (riprovare con log errore) |
| `crawler.transform.system` | WebCrawlerAgent | Trasformare testo scrapato in documenti strutturati |

---

## 3. Codice che orchestra il flusso

| File | Ruolo |
|------|-------|
| `agent/knowledge_base.py` | Costruisce l'indice FAISS ed esegue la ricerca vettoriale (`C64KnowledgeBase.query()`) |
| `agent/researcher.py` | Query expansion, language detection, HyDE, chiamata alla Knowledge Base |
| `agent/coder.py` | Costruisce il prompt finale (system + contesto tecnico + query) e chiama Qwen |
| `agent/model_backend.py` | Backend di generazione: `ModelBackend` (HF Transformers) o `LlamaCppBackend` (GGUF) |
| `agent/orchestrator.py` | Coordina Researcher → Coder → Validator, ciclo self-healing |
| `utils/prompt_manager.py` | Carica e renderizza i template YAML con Jinja2 |

---

## 4. Configurazione

| File | Parametri chiave |
|------|------------------|
| `config/agent_config.yaml` | `model_name: Qwen/Qwen2.5-Coder-1.5B-Instruct`, `temperature: 0.3`, `rag.k: 3`, `rag.use_hyde: true`, `rag.chunk_size: 500` |

---

## 5. Flusso end-to-end

```
Domanda utente
       │
       ▼
┌────────────────────────────────────────────────┐
│ ResearcherAgent                                │
│  1. Query expansion (Qwen)                     │
│  2. Language detection (Qwen)                  │
│  3. HyDE — risposta ipotetica (Qwen, opz.)     │
│  4. FAISS similarity search sui chunk della KB │
│     (knowledge_base/ + data/output/ + ...)     │
└────────────────────┬───────────────────────────┘
                     │ contesto tecnico (chunk rilevanti)
                     ▼
┌────────────────────────────────────────────────┐
│ CoderAgent                                     │
│  Costruisce il prompt:                         │
│    <|im_start|>system                          │
│    {coder.base.system da prompts.yaml}         │
│                                                │
│    CONTESTO TECNICO:                           │
│    {chunk recuperati dalla FAISS}              │
│    <|im_end|>                                  │
│    <|im_start|>user                            │
│    {domanda originale}                         │
│    <|im_end|>                                  │
│    <|im_start|>assistant                       │
│       │                                        │
│       ▼                                        │
│  Qwen/Qwen2.5-Coder-1.5B-Instruct             │
│  (via ModelBackend o LlamaCppBackend)          │
└────────────────────┬───────────────────────────┘
                     │ codice / risposta generata
                     ▼
┌────────────────────────────────────────────────┐
│ ValidatorAgent (solo codice)                   │
│  - BASIC: linee sequenziali, collisioni var.   │
│  - Assembly: branch range (+/- 127), ACME asm  │
│  - Cycle counting                              │
└────────────────────┬───────────────────────────┘
                     │ se fallisce → self-healing loop
                     │ (max 3 tentativi con log errore)
                     ▼
            Risposta finale all'utente
```

---

## 6. Nota importante

Qwen **non** è fine-tunato di base sul C64. La conoscenza tecnica arriva interamente dai chunk della Knowledge Base iniettati nel contesto del prompt (RAG). Se la RAG è disattivata, Qwen risponde solo con la sua conoscenza pre-training, che per un modello piccolo (1.5B) è molto limitata su temi C64.

Il training LoRA opzionale (`pipeline/train_lora.py`) addestra Qwen su `dataset_unified.jsonl` (derivato dagli stessi libri), producendo pesi specializzati in `data/models/c64-lora-pro/`.

---

## 7. Knowledge Distillation (novità)

Il sistema di distillazione permette di **trasferire la conoscenza C64 nei pesi di Qwen** tramite Teacher→Student training.

### Architettura

```
Teacher (modello grande)          Student (Qwen 1.5B)
       │                                │
       │  Legge KB chunks               │  Assorbe conoscenza
       │  Genera QA sintetiche          │  via LoRA fine-tuning
       ▼                                ▼
┌─────────────────┐           ┌──────────────────┐
│ KnowledgeDistiller│ ───────→ │   LoRA Training   │
│ pipeline/        │ dataset   │   pipeline/       │
│ knowledge_       │ JSONL     │   train_lora.py   │
│ distiller.py     │           │                   │
└─────────────────┘           └──────────────────┘
       │                                │
       ▼                                ▼
data/output/distill_dataset.jsonl    data/models/c64-lora-pro/
```

### Teacher predefinito: OpenCode (gratuito)

Il backend `opencode` usa l'assistente OpenCode come Teacher. Nessuna API key, nessun costo.

Altri Teacher configurabili:

| Backend | Config | Costo |
|---------|--------|-------|
| OpenCode | `type: opencode` | $0 |
| Groq | `type: groq` | $0 (free tier) |
| OpenRouter | `type: openrouter` | ~$1-3 |
| Ollama (locale) | `type: ollama` | $0 |
| HuggingFace | `type: huggingface` | $0 (free tier) |

### Tipi di dati sintetici generati

| Tipo | Esempio |
|------|---------|
| Factual Q&A | "Quale registro abilita gli sprite?" → $D015 |
| Code Generation | "Scrivi raster interrupt a riga 100" → {codice} |
| Code Explanation | "Spiega come funziona ADSR" → {spiegazione} |
| Bug Fixing | "Perché questo codice non funziona?" → {correzione} |
| Theory | "Cosa sono le modalità di indirizzamento?" → {teoria} |

### Comandi rapidi

```bash
# Addestrare Qwen con il dataset distillato
python pipeline/train_lora.py data/output/distill_dataset.jsonl

# Generare nuovo dataset con Teacher esterno
python pipeline/knowledge_distiller.py --teacher groq --generate

# Generare dataset con Teacher OpenRouter
python pipeline/knowledge_distiller.py --teacher openrouter --model qwen/qwen3-32b --generate
```

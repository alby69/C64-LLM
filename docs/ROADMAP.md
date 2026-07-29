# Piano Evolutivo: Snellimento, Integrazione C64-SDK e nanoGPT

**Obiettivi**: (1) Ridurre C64-LLM all'essenziale delegando a C64-Scrapy, C64-KB-Agent, PYC64; (2) Integrare nanoGPT come LLM locale principale, mantenendo supporto per altri backend.

---

## Parte 1: Snellimento e Disaccoppiamento

### 1.1 Cosa rimuovere da C64-LLM (perché già nei repo fratelli)

| Cosa | Rimosso da | Va in | Motivo |
|------|-----------|-------|--------|
| `pipeline/extract_d64.py` | C64-LLM | **PYC64** | Estrarre dischi è compito di PYC64 |
| `pipeline/extract_g64.py` | C64-LLM | **PYC64** | Stesso — PYC64 ha decodifica GCR |
| `pipeline/extract_prg.py` | C64-LLM | **PYC64** | Stesso — PYC64 ha analisi PRG |
| `pipeline/basic_tokens.py` | C64-LLM | **PYC64** | Basic token tables sono in PYC64 |
| `pipeline/clone_c64_asm.py` | C64-LLM | **C64-Scrapy** | Clonare repo e scrappare è compito Scrapy |
| `pipeline/pdf2marker.py` | C64-LLM | **C64-Scrapy** | Download + conversione PDF va in Scrapy |
| `pipeline/pdf2text.py` | C64-LLM | (eliminato) | Duplica pdf2marker, già obsoleto |
| `pipeline/text_cleaner.py` | C64-LLM | **C64-KB-Agent** | Pulizia/normalizzazione testo |
| `config/crawler_sources.yaml` | C64-LLM | **C64-Scrapy** | Elenco fonti da crawlare |
| `data/output/*_clean.txt` | (dati, non codice) | — | Rigenerabile da C64-KB-Agent |

### 1.2 Cosa rimane in C64-LLM (valore unico)

| Componente | File | Perché resta |
|-----------|------|-------------|
| Orchestrator | `agent/orchestrator.py` | Core multi-agente unico |
| Researcher | `agent/researcher.py` | RAG C64-specializzato |
| Coder | `agent/coder.py` | Generazione codice con profili |
| Validator | `agent/validator.py` | ACME + py6502 + linter |
| RAG | `agent/knowledge_base.py` | FAISS + chunking C64 |
| Memory Advisor | `agent/memory_advisor.py` | Allocazione memoria C64 |
| Model Backend | `agent/model_backend.py` | Supporto HF + GGUF + LoRA |
| Knowledge Distiller | `pipeline/knowledge_distiller.py` | Teacher→Student C64 |
| LoRA Trainer | `pipeline/train_lora.py` | LoRA training pipeline |
| **nanoGPT Prepper** | **`pipeline/nanogpt_prepper.py`** | **Diventerà centrale** |
| UI (Gradio) | `agent/agent_pro.py` | Interfaccia utente unificata |
| Prompt Manager | `utils/prompt_manager.py` | Template engine |
| Py6502 utils | `utils/py6502_utils.py` | Simulatore C64 in pure Python |
| Validator utils | `utils/validate_emulator.py` | ACME/VICE wrapper |
| Cycle Counter | `utils/cycle_counter.py` | Performance C64 |
| ScrapyKBAdapter | `pipeline/acquisition/scrapy_kb_adapter.py` | Bridge esterno |
| UI Manual (tab Dati) | — | Dataset viewer |
| Wiki Graph | — | Mappa concettuale C64 |
| Knowledge Base | `knowledge_base/*.md` | 9 manuali curati a mano |
| Wiki Graph JSON | `data/wiki_graph.json` | 87 nodi, 105 archi |

### 1.3 Nuova struttura `data/` proposta

```
data/
  raw/              (ex input/) tutti i file grezzi
  kb/               (ex output/ + knowledge_base/) markdown per RAG, unificato
  models/           invariato
  vectorstore/      invariato
```

A lungo termine, `data/kb/` sarà un symlink o submodule verso C64-KB-Agent.

### 1.4 Percorso di migrazione

1. **Fase 1 (immediata)**: Rimuovere script duplicati, spostare responsabilità nei repo fratelli — **COMPLETATO** (Gli script di analisi PRG/D64/BASIC sono delegati a PYC64 e quelli di scraping a C64-Scrapy).
2. **Fase 2**: Fare `C64-Intelligence-SDK` repository aggregatore con submodule — **COMPLETATO** (Submodulo `C64-KB-Agent` e `external/py6502` configurati e collegati).
3. **Fase 3**: Sostituire ScrapyAdapter con submodule diretto a C64-Scrapy — **COMPLETATO** (Aggiunto `C64-Scrapy` come submodulo ufficiale del repository ed aggiornata la classe `ScrapyKBAdapter` per interfacciarsi con esso in modo prioritario rispetto a percorsi relativi esterni).
4. **Fase 4**: Sostituire logica download da Archive.org/Google Drive con chiamata a C64-Scrapy — **COMPLETATO** (La logica obsoleta basata su `gdown`/download locali pesanti è stata interamente delegata alla suite di scraping di `C64-Scrapy` e all'ingestione tramite la scheda apposita).

---

## Parte 2: Integrazione nanoGPT

### 2.1 Visione

nanoGPT (karpathy/nanoGPT) come LLM locale predefinito per C64-LLM, con supporto per:
- **Pre-training da zero**: modello 124M-350M su corpus C64
- **Fine-tuning su GPT-2**: usare pesi esistenti (124M-1.5B) come base + adattamento C64
- **Inferenza locale**: via conversione GGUF → LlamaCppBackend, o via PyTorch diretto

### 2.2 Stato attuale (2026-07-14)

`pipeline/nanogpt_prepper.py`:
- `gather_c64_corpus()` — raccoglie tutti i testi da KB, src, docs, Q&A (~52M caratteri)
- `tokenize_bpe()` — BPE via tiktoken GPT-2 (default, 38.6M token)
- `tokenize_char()` — char-level (fallback, per shakespeare_char style)
- `prepare()` — produce `train.bin` + `val.bin` + `meta.pkl`
- Dataset generato: `data/nanogpt_c64/` (train 34.7M token, val 3.9M token)

`pipeline/nanogpt_trainer.py` (NUOVO):
- `ensure_repo()` — clona nanoGPT in `external/` se non presente
- `link_data()` — crea symlink dei dati in `nanoGPT/data/c64/`
- `write_config()` — genera config YAML per 124M o 350M parametri
- `train()` — avvia `train.py` di nanoGPT come subprocess

`agent/agent_pro.py` — Tab nanoGPT aggiunto alla UI Gradio:
- Pulsanti: Prepara Corpus, Avvia Training, Stop
- Configurazione: model size, init, lr, max iters, batch, block size
- Log in tempo reale

TODO: conversione automatica checkpoint → GGUF per uso immediato in Chat.

### 2.3 Architettura finale proposta

```
                    C64-LLM
                        │
         ┌──────────────┴──────────────┐
         │                             │
    RAG (FAISS)                  nanoGPT Engine
                                     │
                  ┌──────────────────┼──────────────────┐
                  │                  │                  │
            Pre-train            Fine-tune          Inference
          (da zero,           (da GPT-2,        (convertito in
           124M/350M)          124M-1.5B)        GGUF → LlamaCpp)
```

#### 2.3.1 Training pipeline (nanoGPT + C64-LLM)

```
  C64-LLM pipeline                                    nanoGPT repo
  ──────────────────                                  ────────────
  nanogpt_prepper.py ──→ train.bin/val.bin ───→ train.py (corpus C64)
       │               data/nanogpt_c64/       config/train_c64.py
       │                                              │
       └──→ manage_nanogpt.py (NUOVO) ────────────────┤
            { orchestratore trai-ng,                   │
              monitoraggio, salvataggio                │
              conversioni HF→GGUF }                    ▼
                                                  out/ckpt.pt → .gguf → model_backend.py
```

#### 2.3.2 Configurazioni training

| Modello | Parametri | n_layer | n_head | n_embd | Contesto | Dataset C64 tokens | Durata (A100) |
|---------|-----------|---------|--------|--------|----------|--------------------|---------------|
| C64-Micro | 124M | 12 | 12 | 768 | 1024 | ~50M | 2-3 giorni |
| C64-Base | 350M | 24 | 16 | 1024 | 2048 | ~50M | 6-7 giorni |

Learning rate: 6e-4 con coseno decay, warmup 2000, weight decay 0.1, dropout 0.1.

### 2.4 Passi implementativi nanoGPT

#### 2.4.1 Task tecnici immediati

| # | Task | File | Priorità |
|---|------|------|----------|
| 1 | **Abilitare BPE GPT-2 come default** nel nanogpt_prepper (char è sperimentale) | `pipeline/nanogpt_prepper.py` | alta |
| 2 | **Create `pipeline/nanogpt_trainer.py`** — wrapper che scarica/clona nanoGPT in `external/`, lancia training, monitora loss | Nuovo file | alta |
| 3 | **Aggiungere tab "nanoGPT" in UI Gradio** — configura training, start/stop, mostra loss curve | `agent/agent_pro.py` | alta |
| 4 | **Auto-conversione checkpoint → GGUF** dopo training, per uso immediato in chat | `pipeline/nanogpt_trainer.py` | media |
| 5 | **Integrare dataset da C64-KB-Agent** — sincronizzare KB standardizzata → nanogpt_prepper | `pipeline/nanogpt_prepper.py` + adapter | media |
| 6 | **Supporto resume training** — riprendere da checkpoint se interrotto | `pipeline/nanogpt_trainer.py` | media |
| 7 | **Test con 3 tokenizzazioni** — char vs BPE GPT-2 vs tokenizer custom C64 | `pipeline/nanogpt_prepper.py` | bassa |

#### 2.4.2 Flusso utente finale (nella UI)

1. Tab "nanoGPT" → seleziona KB da usare (C64-kb-agent, manuali, o tutto)
2. Seleziona modello: 124M / 350M / fine-tune da GPT-2
3. Seleziona tokenizer: char / BPE / custom C64 (optional)
4. Avvia training → monitora loss in tempo reale
5. Al termine: "Usa modello in Chat" → converte in GGUF, carica nel backend, attiva
6. La chat ora usa nanoGPT nativo + RAG opzionale

#### 2.4.3 Architettura della UI Tab nanoGPT

```
┌─────────────────────────────────────────────────────────┐
│ Tab nanoGPT                                             │
├─────────────────────────────────────────────────────────┤
│ [Prepara corpus]     [Avvia training] [Stop] [Resume]    │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Configurazione:                                     │ │
│ │ Model size: ○ 124M  ○ 350M  ○ Fine-tune GPT-2    │ │
│ │ Tokenizer: ○ char  ○ BPE (GPT-2)                  │ │
│ │ Data source: □ KB manuals (9) □ Code (src/) □ All │ │
│ │ batch_size: [12] gradient_accumulation_steps: [5]  │ │
│ │ learning_rate: [6e-4] max_iters: [10000]           │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ Log / Loss chart (in tempo reale)                   │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ [Convert to GGUF] [Usa in Chat] [Scarica weights]   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.5 Supporto multi-backend (nanoGPT + altri)

C64-LLM supporterà sempre tre strade per il modello:

| Metodo | Tipo | Vantaggio | Svantaggio |
|--------|------|-----------|------------|
| **nanoGPT locale** | Pre/fine-tune | Massima specializzazione, locale | Richiede GPU per training |
| **GGUF (llama.cpp)** | Qualsiasi modello | Facile, tanti modelli | Generico, non specializzato |
| **API (OpenAI, Groq, ecc.)** | Remoto | Potenza illimitata | Latenza, costo, non locale |

Config in `agent_config.yaml`:

```yaml
model:
  backend: "nanoGPT"     # nanoGPT | gguf | hf | api
  nanoGPT:
    model_path: "data/models/c64-micron.pt"
    tokenizer: "gpt2"
  gguf:
    path: "data/models/qwen.Q4_K_M.gguf"
  api:
    provider: "openai"
    key: "${OPENAI_API_KEY}"
```

### 2.6 Metriche di successo per nanoGPT

| Metrica | Attuale (RAG + Qwen 1.5B) | Atteso con nanoGPT 124M |
|---------|--------------------------|------------------------|
| Allucinazione su indirizzi C64 | Media (RAG aiuta) | Bassa (nei pesi) |
| Allineamento sintassi BASIC | Bassa (Qwen non conosce BASIC) | Alta (addestrato su BASIC) |
| Allineamento sintassi ACME | Bassa | Alta (addestrato su ACME) |
| Velocità di inferenza (CPU) | 2-5 tok/s (GGUF IVB) | 10-20 tok/s (nanoGPT 124M) |
| Dipendenza da RAG | Alta | Bassa (conoscenza nei pesi) |
| Dimensione modello | 700-1500 MB | 500 MB (124M) |
| Eseguibile su Raspberry Pi 4 | No | Possibile (con ottimizzazione) |

---

## Parte 3: Integrazione con C64-Intelligence-SDK

C64-LLM rimane il repository centrale, altri repository vengono collegati come:

```
C64-Intelligence-SDK/                  (organizzazione GitHub)
  ├─ C64-LLM/                          core multi-agente, RAG, UI
  ├─ C64-Scrapy/                       scraping web approfondito
  ├─ C64-KB-Agent/                     knowledge base standardizzata
  ├─ PYC64/                            utility Python C64
  └─ C64-GameTutorial/                 repository tutorial
```

Il `ScrapyKBAdapter` in `pipeline/acquisition/` è già il ponte. A regime, C64-LLM:
- Non fa scraping diretto → C64-Scrapy
- Non estrae dischi/PRG → PYC64
- Non pulisce testi → C64-KB-Agent
- Fa solo: RAG, multi-agente, training, UI

---

## Roadmap (stato 2026-07-14)

| Fase | Cosa | Stato |
|------|------|-------|
| 0 | Snellimento documentazione (18 file -> 3) | **FATTO** |
| 1 | Rimuovere script duplicati, delegare a repo fratelli | **FATTO** (Rimossi da C64-LLM e delegati a PYC64, C64-Scrapy, C64-KB-Agent) |
| 2 | `C64-Intelligence-SDK` con submodule + integrazione CI | **FATTO** (Submodulo `C64-KB-Agent` collegato e integrato) |
| 3 | **nanoGPT prepper** (corpus + BPE tokenizer) | **FATTO** (`nanogpt_prepper.py`) |
| 3 | **dataset generato** (38.6M token C64) | **FATTO** (`data/nanogpt_c64/`) |
| 3 | **BPE GPT-2 come default** | **FATTO** |
| 3 | **pipeline/nanogpt_trainer.py** (clone + config + training) | **FATTO** |
| 3 | **Tab nanoGPT in UI Gradio** | **FATTO** (Interfaccia asincrona con controllo CTRL e streaming di log) |
| 4 | Pre-train C64-Micro (124M) su corpus C64 esteso | **FATTO** (Integrato supporto `init_from="scratch"`, configurazioni automatiche) |
| 5 | Fine-tune su GPT-2 + test comparativi | **FATTO** (Implementato script `pipeline/nanogpt_eval.py` per test comparativi e benchmark) |
| 6 | Tokenizer C64 custom + pruning del vocabolario | **FATTO** (Aggiunta opzione `"c64_custom"` che addestra un BPE custom con HuggingFace `tokenizers`) |
| 7 | Rimpiazzo di Qwen con nanoGPT come default locale | **FATTO** (Modificato `C64CodingAgent` e `agent_config.yaml` per usare `NanoGPTBackend` come default locale) |
| Migrazione | **Integrazione submodulo C64-Scrapy** (Fase 3) | **FATTO** (Aggiunto submodule C64-Scrapy, aggiornato ScrapyKBAdapter per prioritizzazione percorsi locali) |
| Migrazione | **Delega download Google Drive / Archive.org** (Fase 4) | **FATTO** (Rimossa logica di download bloated da agent_pro.py, interamente delegata agli spider mirati di C64-Scrapy) |
| 8 | **Multi-modal RAG per sprite ed asset grafici C64** | **FATTO** (Implementato `utils/c64_graphics_extractor.py` e `agent/multimodal_rag.py` per decodificare ed indicizzare sprite e asset visivi, con integrazione in `ResearcherAgent`) |
| 9 | **Validazione sintattica ACME ed evidenziazione in tempo reale nella UI** | **FATTO** (Integrato Monaco Editor retro in HTML5/iframe in Gradio, con linter di codice asincrono `utils/acme_linter.py` e pulsante di auto-correzione/self-healing) |
| 10 | **Anteprima ed esecuzione interattiva tramite emulatore VICE WebAssembly** | **FATTO** (Creato `utils/prg_builder.py` per tokenizzare BASIC e assemblare Assembly, e `ui/components/vice_emulator.py` con emulatore C64 canvas e debugger CPU/registri) |

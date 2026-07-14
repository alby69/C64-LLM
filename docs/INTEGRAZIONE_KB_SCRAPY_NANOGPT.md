# Integrazione Multi-Repository (Scrapy -> KB-Agent -> LLM) e Studio di Fattibilità nanoGPT per Commodore 64

Questo documento analizza in profondità l'architettura dei tre repository del sistema, definisce la strategia di ottimizzazione per il collegamento di **C64-LLM** con **C64-KB-Agent** e **C64-Scrapy**, e presenta uno studio di fattibilità dettagliato per l'addestramento di un modello specializzato tramite **nanoGPT**.

---

## 1. Architettura Multi-Repository e Flusso dei Dati

L'ecosistema di intelligenza sul Commodore 64 è organizzato come una pipeline a tre livelli disaccoppiati, in cui ogni componente ha responsabilità ben definite:

```
┌──────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│    C64-Scrapy    │ ───> │    C64-KB-Agent     │ ───> │       C64-LLM       │
│                  │      │                     │      │                     │
│  - Web Scraping  │      │ - standardizzazione │      │ - RAG (FAISS)       │
│  - Spiders Wiki  │      │ - pulizia metadati  │      │ - Multi-Agent Core  │
│  - PDF/Books     │      │ - validazione KB    │      │ - Self-Healing      │
└──────────────────┘      └─────────────────────┘      └─────────────────────┘
```

1. **C64-Scrapy**: È il motore di acquisizione proattiva. Contiene spider Scrapy specializzati per scansionare siti come *Codebase64*, *C64-Wiki*, *Lemon64* ed estrarre documentazione tecnica in formato grezzo.
2. **C64-KB-Agent**: Funge da *Hub della Conoscenza* (Knowledge Base Agent). Raccoglie gli output di Scrapy, li pulisce da ridondanze, uniforma il frontmatter YAML (es. tag, categorie, boost) e organizza i file in directory logiche. Può anche esporre questa conoscenza tramite un'API lightweight o un archivio Git consolidato.
3. **C64-LLM (Questo Repo)**: È il motore di ragionamento ed esecuzione. Ingestisce i dati standardizzati da `C64-KB-Agent`, costruisce o aggiorna l'indice FAISS del RAG, ed esegue il ragionamento multi-agente (Orchestrator, Coder, Validator) con simulatore `py6502` e compilazione ACME.

---

## 2. Ottimizzazione di C64-LLM per il Collegamento

Per integrare ed ottimizzare `C64-LLM` affinché consumi in modo robusto i dati provenienti da `C64-KB-Agent`, implementiamo i seguenti interventi:

### A. Strategia di Ingestione Diretta (Disaccoppiata)
Piuttosto che rieseguire crawler instabili all'interno del LLM, `C64-LLM` si appoggia interamente alla struttura dati esposta da `C64-KB-Agent`. Introduciamo un **ScrapyKBAdapter** (`pipeline/acquisition/scrapy_kb_adapter.py`) che automatizza:
- Il rilevamento di nuovi file markdown in `C64-KB-Agent`.
- Il parsing robusto del frontmatter YAML (per preservare tag e metadati utili al RAG).
- Il syncing efficiente (basato su hash MD5 per evitare indicizzazioni ridondanti) in `data/kb/scraped/`.

### B. Standardizzazione delle Directory (Allineamento Refactoring Plan)
I dati sincronizzati vengono inseriti nella nuova struttura dati minimalista descritta nel `REFACTORING_PLAN.md`:
- `data/kb/scraped/`: Contiene i file markdown generati da `C64-Scrapy` e validati da `C64-KB-Agent`.
- `data/kb/manuali/`: Contiene i manuali curati originariamente posti in `knowledge_base/`.

### C. Configurazione Centralizzata
Includiamo le impostazioni dei repository esterni in `config/agent_config.yaml`:
```yaml
kb_agent:
  enabled: true
  repo_path: "../C64-KB-Agent"          # Percorso locale del sottomodulo o repo KB-Agent
  scraped_subpath: "data/scraped"       # Subpath dei file markdown prodotti da Scrapy
  sync_on_startup: false
```

---

## 3. Studio di Fattibilità: nanoGPT per un LLM C64 Specializzato

**nanoGPT** di Andrej Karpathy è il repository di riferimento per l'addestramento e il fine-tuning di GPT di medie/piccole dimensioni (da 124M a 1.5B di parametri).

L'utilizzo di nanoGPT per creare un LLM specializzato sulla Knowledge Base del C64 (Assembly 6502 e BASIC v2) è **estremamente promettente** e tecnicamente realizzabile per i seguenti motivi.

### 3.1 Motivazioni della Scelta
1. **Dominio Altamente Specifico (Basso Livello)**: I modelli commerciali generali (es. Llama, Qwen) faticano con i dettagli dell'Assembly 6502, con i registri hardware del VIC-II ($D020-$D02F) e del SID, e con i dialetti del BASIC v2. Un modello specializzato apprende l'intima relazione tra istruzioni, cicli di clock e indirizzi di memoria.
2. **Efficienza e Latenza**: Un modello compatto (es. 124M o 350M parametri) addestrato su nanoGPT ha tempi di inferenza nell'ordine dei millisecondi e può girare localmente su CPU standard o Raspberry Pi senza richiedere GPU high-end.
3. **Formati e Sintassi**: L'addestramento pre-train o il fine-tuning approfondito insegna al modello la sintassi esatta di ACME Assembler e l'ordinamento rigoroso delle linee BASIC senza "allucinare" direttive moderne.

### 3.2 Preparazione del Dataset e Tokenizzazione

Per alimentare nanoGPT, dobbiamo convertire l'intera Knowledge Base in file binari di token pre-elaborati.

#### A. Tokenizzazione: Custom vs standard (BPE)
- **Opzione BPE (tiktoken / GPT-2/4)**: Usare il tokenizer di GPT-2 (`gpt2`) è la scelta consigliata per il transfer learning o per iniziare rapidamente. Tuttavia, le stringhe di codice Assembly (es. `LDA #$01`, `STA $D020`) vengono frammentate in molti sotto-token insoliti.
- **Opzione Tokenizer Custom**: Creare un tokenizer custom basato su caratteri o su un vocabolario specializzato C64 (che includa mnemonici Assembly 6502 e keyword BASIC come token singoli, es. `[LDA]`, `[STA]`, `[POKE]`, `[SYS]`). Questo dimezzerebbe la lunghezza delle sequenze, raddoppiando l'efficienza computazionale del contesto.

#### B. Pipeline di Pre-Tokenizzazione (`pipeline/nanogpt_prepper.py`)
Sviluppiamo uno script per esportare la KB (markdown, dataset JSONL, sorgenti) in un unico stream testuale pulito, tokenizzarlo e salvarlo in file Numpy `train.bin` e `val.bin`.

### 3.3 Architettura del Modello e Parametri di Training

Per un dominio focalizzato sul C64, proponiamo due configurazioni:

| Parametro | Modello "C64-Micro-GPT" (Consigliato) | Modello "C64-Medium-GPT" |
| :--- | :--- | :--- |
| **Parametri** | ~124M (stile GPT-2) | ~350M (stile GPT-2 Medium) |
| **n_layer** | 12 | 24 |
| **n_head** | 12 | 16 |
| **n_embd** | 768 | 1024 |
| **Block Size (Contesto)** | 1024 o 2048 | 2048 |
| **Dimensione Vocabolario**| 50,257 (GPT-2 tokenizer) | 50,257 |

#### Configurazione dell'Addestramento (Training Schedule)
- **Dataset Size**: La KB completa del C64 + sorgenti storici contiene circa 10-50 milioni di token.
- **Learning Rate**: `6e-4` con decadimento del coseno fino a `6e-5`.
- **Warmup Itrs**: 2000 iterazioni.
- **Batch Size**: `batch_size = 12` con `gradient_accumulation_steps = 5` per ottenere una batch globale effettiva di 60 sequenze.
- **Regolarizzazione**: Weight decay `0.1`, dropout `0.1` (importante per prevenire overfitting dato che il dataset è specialistico).

### 3.4 Flusso di Integrazione in C64-LLM

Una volta addestrato il modello con nanoGPT:
1. **Esportazione in HuggingFace**: Esportiamo i pesi PyTorch nel formato standard di HuggingFace `AutoModelForCausalLM`.
2. **Conversione in GGUF**: Utilizziamo il tool `convert_hf_to_gguf.py` di `llama.cpp` per convertire il modello nel formato `.gguf`.
3. **Integrazione nel Backend**: Il modello convertito viene posto in `data/models/` e caricato istantaneamente tramite `LlamaCppBackend` in `agent/model_backend.py`.
4. **Coesistenza con il RAG**: Il modello specializzato non sostituisce il RAG, ma vi collabora. Il RAG fornisce i registri precisi o le routine specifiche (declarative memory), mentre l'LLM nanoGPT genera codice sintatticamente impeccabile senza allucinazioni.

---

## 4. Conclusione ed Ecosistema Futuro

L'unione di **C64-Scrapy**, **C64-KB-Agent**, **C64-LLM** e l'addestramento con **nanoGPT** rappresenta il culmine tecnologico per preservare e potenziare lo sviluppo su sistemi retrocomputing. Il disaccoppiamento dei moduli assicura scalabilità, mentre nanoGPT apre le porte a modelli locali fulminei, super-specializzati e privi di sovrastrutture moderne.

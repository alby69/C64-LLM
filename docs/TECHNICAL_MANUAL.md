# Manuale Tecnico Completo: C64 Coding Agent

Questo documento rappresenta la risorsa definitiva per l'architettura, il funzionamento e l'evoluzione del C64 Coding Agent.

## 1. Visione d'Insieme

Il C64 Coding Agent è un sistema multi-agente progettato per assistere nello sviluppo di software per Commodore 64 (Assembly 6502 e BASIC v2). Combina una pipeline di dati proattiva (Crawler + RAG) con un'architettura di ragionamento strutturata (Chain-of-Thought) e un ciclo di validazione con self-healing.

Per una panoramica dettagliata delle responsabilità core e del flusso dati, consultare [ARCHITETTURA_E_COMPITI.md](ARCHITETTURA_E_COMPITI.md).

---

## 2. Architettura degli Agenti

Il sistema opera tramite la collaborazione di 5 agenti core, coordinati da un Orchestratore centrale.

### 2.1 OrchestratorAgent (Coordinamento e Self-Healing)
È il cervello del sistema. Gestisce il ciclo di vita di una richiesta:
1.  **Analisi & Ricerca**: Attiva il `Researcher` per ottenere il contesto tecnico.
2.  **Generazione**: Passa query e contesto al `Coder`.
3.  **Validazione**: Invia il codice generato al `Validator`.
4.  **Self-Healing**: Se la validazione fallisce, attiva un ciclo di correzione automatica (fino a 3 tentativi) fornendo i log d'errore al Coder.

### 2.2 ResearcherAgent (RAG)
Specializzato nel recupero di informazioni dalla "Knowledge Engine":
- **Query Expansion**: Trasforma richieste vaghe in termini tecnici C64.
- **HyDE (Hypothetical Document Embeddings)**: Disabilitato di default (`use_hyde: false`). Il modello 1.5B generava risposte ipotetiche allucinate che peggioravano il retrieval. Sostituito da `k_results=10` e chunk più ampi.
- **Graph Navigation**: Supporta Wiki-links in stile Obsidian per navigare tra documenti correlati (es. da "VIC-II" a "Sprite Registers").
- **PDF filtering**: I file `data/output/*_clean.txt` sono inclusi nell'indice solo se superano un filtro keyword (≥15 termini tecnici C64), per escludere artefatti OCR di bassa qualità.
- **Marker output (.md)**: I file `.md` prodotti da marker-pdf (layout detection, OCR, markdown strutturato) sono inclusi con source_boost=1.2, prioritari rispetto ai `_clean.txt` legacy (boost=0.3). Se marker-pdf non è installato, viene usato PyMuPDF come fallback (solo `.txt`, nessun `.md`).

### 2.3 CoderAgent (Sintesi di Codice)
L'agente esecutivo che scrive il codice:
- **Expert Profiles**: Assume personalità diverse (BASIC Expert o Assembly Expert) in base al task.
- **Chain-of-Thought (CoT)**: Ogni risposta include una sezione di pianificazione logica prima dell'implementazione.
- **Addressing Mode Awareness**: Ottimizzato per scegliere le modalità di indirizzamento corrette (Zero Page vs Absolute).

### 2.4 ValidatorAgent (Analisi Statica e Compilazione)
Garantisce la qualità del codice:
- **Assembly**: Integra l'assembler ACME. Esegue check preventivi su branch fuori range (+/- 127 byte) e terminazione delle routine (RTS/JMP). Se il codice Assembly non inizia con una direttiva origine (`* =`), il validatore prepone automaticamente `* = $C000` per evitare l'errore ACME "Program counter undefined".
- **BASIC v2**: Parser interno per:
    - Numeri di riga sequenziali.
    - Collisioni di variabili (considera solo i primi 2 caratteri, es. `SCORE1` vs `SCORE2`).
    - Range di POKE/PEEK e bilanciamento FOR/NEXT.
- **Cycle Counter**: Fornisce una stima dei cicli di clock per le routine Assembly.

### 2.5 WebCrawlerAgent (Acquisizione Conoscenza)
Agente proattivo che monitora fonti autorevoli (C64-Wiki, GitHub, Zimmers, Archive.org) per mantenere aggiornato il Knowledge Base locale.

### 2.5.1 Download Intelligente da Archive.org
Quando viene inserito un URL di Archive.org, il sistema:
1. **Analizza i metadati** dell'item via API (`metadata/{item_id}`)
2. **Seleziona il miglior formato testuale** con priorità: **TXT > EPUB > HTML > PDF**
3. **Scarica un solo file** (il migliore disponibile, non tutti i PDF)
4. **Estrae il testo** in base al formato:
   - `.txt`: copia diretta
   - `.epub`: decompone ZIP, estrae testo da XHTML/HTML con `HTMLParser` stdlib (fallback `pandoc`)
   - `.html`/`.htm`: pulisce tag HTML con `HTMLParser` stdlib
   - `.pdf`: estrazione via pdf2marker (marker-pdf: layout detection, OCR, produce .md strutturato + .txt + .meta.json)
5. **Pipeline**: text_cleaner (solo su .txt) → build_dataset → rebuild KB (include .md da marker con boost 1.2)
6. Gli eventuali file D64/G64/PRG vengono scaricati ed estratti in parallelo

### 2.5.2 Download da Google Drive

Quando viene inserito un URL di Google Drive (`/drive/folders/<id>`), il sistema:
1. **Enumera i file** nella cartella con `gdown.download_folder(skip_download=True)` (nessun download effettivo)
2. **Mostra riepilogo**: numero di file trovati, raggruppati per sottocartella
3. **Scarica file per file** con `gdown.download(id, output, quiet=True)`
4. **Fallback**: se gdown fallisce (rate limiting), riprova con `requests` su `https://drive.google.com/uc?id=<id>&export=download&confirm=t`, verificando che il content-type non sia `text/html`
5. **Delay**: 1.5 secondi tra file per evitare rate limiting
6. **Pipeline**: tutti i PDF scaricati vengono processati: pdf2marker → text_cleaner (su .txt) → build_dataset → rebuild KB (include .md da marker con boost 1.2)

### 2.5.3 Auto-elabora Link dalla Chat

La checkbox "Auto-elabora link" nell'interfaccia Chat attiva un flusso automatico:
1. Dopo la risposta dell'agente, vengono estratti tutti gli URL dal messaggio utente e dalla risposta
2. Ogni URL viene aggiunto a `data/custom_sites.json` (saltando duplicati)
3. Per ogni URL, viene eseguita `download_and_integrate()` che avvia la pipeline completa
4. Il progresso viene mostrato in tempo reale nella chat tramite yield del generatore

---

## 3. Knowledge Engine (RAG)

Il sistema RAG (Retrieval-Augmented Generation) è il cuore della precisione tecnica dell'agente.
- **Vault Obsidian**: La documentazione è strutturata in Markdown (9 manuali: `vic2_registers.md`, `raster_interrupts.md`, `sprite_programming.md`, `sid_programming.md`, `kernal_routines.md`, `6502_addressing_modes.md`, `c64_screen_routines.md`, `c64_basic_tutorial.md`, `c64_memory_map.md`) con frontmatter YAML per tag e categorie.
- **Indicizzazione**: Utilizza `sentence-transformers/all-MiniLM-L6-v2` per creare embedding vettoriali memorizzati in FAISS.
- **Pipeline**: Include marker-pdf per conversione PDF→Markdown con layout detection e OCR, e text_cleaner per normalizzare il testo estratto da PDF tecnici e magazine storici (The Transactor, Compute!, ecc.).
- **Inclusione PDF filtrata**: I file `data/output/*_clean.txt` (estrazioni OCR da PDF tecnici) sono inclusi con filtro keyword (≥15 termini C64, >1KB, boost=0.3). I file `.md` prodotti da marker-pdf sono inclusi con boost 1.2, dando priorità al markdown strutturato. Imposta `SKIP_PDF=1` per escluderli. I `.md` curati rimangono la fonte principale.

---

## 3.1 Knowledge Base — Ricerca File nella UI

Il tab **Knowledge Base** include una sezione "Esplora file KB" con:
- **Elenca tutti i file**: mostra ricorsivamente tutti i file in `knowledge_base/`, `data/input/`, `data/src/`
- **Cerca file**: filtro case-insensitive per nome file o percorso, utile per verificare se un file è già stato inserito
- **Anteprima file**: dropdown + pulsante per visualizzare le prime 50 righe di un file selezionato

### 3.1.1 Chunking

Lo splitter utilizza `RecursiveCharacterTextSplitter` con:
- `chunk_size=2000`, `chunk_overlap=200`
- Separatori: `["\n\n", "\n", ".", " ", ""]`
- A differenza del vecchio `CharacterTextSplitter(chunk_size=500)`, evita warning e gestisce meglio codice assembly/BASIC preservando la struttura lessicale. Chunk più ampi (2000 vs 1500) migliorano il recall includendo contesto tecnico completo.

### 3.1.2 Encoding Handling

Tutte le letture file nella Knowledge Base usano `encoding="utf-8", errors="replace"` per gestire file binari o corrotti. I formati binari (`.gz`, `.zip`, `.png`, `.pdf`, `.d64`, ecc.) vengono saltati tramite `SKIP_EXTS`.

### 3.1.3 Anteprima File

La funzione `preview_kb_file()` in `agent/agent_pro.py` gestisce l'anteprima dei file nel dropdown Esplora File:
- Il percorso selezionato viene prima verificato così com'è (relativo alla CWD), poi come join con ciascuna directory in `KB_DIRS`
- I file binari vengono intercettati con `UnicodeDecodeError` e mostrano un messaggio esplicito invece di crashare

## 3.2 Technical Terms — Nuvola di Tag

Il tab **Chat** include una sezione "Technical Terms" che mostra una nuvola di tag dei principali termini tecnici C64:
- **Dimensione del tag** = importanza (peso 1-5): registri core e istruzioni frequenti sono più grandi
- **Colore**: sfumatura dal ciano al bianco in base all'importanza
- **Cerca**: casella di testo per filtrare i termini in tempo reale
- **Click**: cliccando un termine viene automaticamente inserito nel campo di input della chat
- **Oltre 150 termini** coperti tra registri VIC-II/SID/CIA, istruzioni 6502, comandi BASIC v2, e concetti (Raster Interrupt, Sprite, ecc.)

---

## 3.3 Dataset Viewer

Il tab **Dati** include un visualizzatore del dataset con:
- **Paginazione**: 20 entry per pagina, navigazione con ◀/▶
- **Ricerca**: filtro case-insensitive su tutte le entry
- **Card orizzontali**: ogni entry JSONL formattata come card HTML con scroll orizzontale (flexbox + overflow-x:auto)
- La struttura JSONL segue: `{"instruction", "context", "constraints", "output"}`

---

## 4. Guide all'Utilizzo e Casi d'Uso

### 4.1 Generazione Raster Interrupt (Assembly)
L'utente chiede un effetto grafico. L'agente recupera i registri VIC-II ($D012), imposta il vettore IRQ ($0314) e valida il codice con ACME.

### 4.2 Classifica in BASIC
L'agente gestisce array (`DIM`) e input, validando che i nomi delle variabili non collidano e che i numeri di riga siano ordinati.

---

## 5. Configurazione e Personalizzazione

Il sistema è altamente configurabile tramite `config/agent_config.yaml`:
- **agent.max_attempts**: Numero di round di self-healing.
- **rag.k**: Numero di chunk recuperati (default: 10).
- **rag.use_hyde**: Disabilitato di default (`false`) — il modello 1.5B allucina risposte ipotetiche.
- **rag.chunk_size**: Dimensione chunk per indicizzazione (default: 1000, KB usa 2000).
- **rag.chunk_overlap**: Overlap tra chunk (default: 200).
- **ui.prompt_library**: Lista di prompt predefiniti nella Gradio UI.

### 5.1 Backend Modello

Supporta due backend configurabili in `agent/model_backend.py`:

| Backend | Quando usato | Configurazione |
|---------|-------------|----------------|
| **LlamaCppBackend** (default) | Se `gguf_path` esiste | `n_ctx=8192`, `n_threads=os.cpu_count()`, file `.gguf` in `/app/data/models/` |
| **ModelBackend** (HF Transformers) | Se nessun GGUF trovato | AutoModelForCausalLM con 4-bit quantization, supporta LoRA tramite PeftModel. Caricamento dinamico: `load_lora(path)` / `unload_lora()` via UI senza riavvio. |

Il contesto (`n_ctx`) è stato portato da 2048 a 8192 per gestire messaggi lunghi (es. risposte da altri LLM).

---

## 6. Knowledge Distillation

Il sistema di Knowledge Distillation è progettato per specializzare un modello Student (Qwen2.5-Coder-1.5B-Instruct) sulla programmazione C64 (Assembly 6502 e BASIC v2) usando un Teacher LLM che genera dati sintetici di training dalla Knowledge Base.

### 6.1 Architettura

```
Knowledge Base (*.md) 
       │
       ▼
 KnowledgeChunkLoader
  - Carica chunk da documento KB
  - Filtra chunk duplicati
  - Supporta ogni chunk come contesto indipendente
       │
       ▼
    Teacher LLM (5 backends)
  - opencode → Assistente stesso (nessuna API key)
  - groq    → Groq API (Mixtral, Llama3, ecc.)
  - openrouter → OpenRouter (GPT-4o, Claude, ecc.)
  - ollama  → Ollama locale
  - huggingface → HuggingFace Inference API
       │
       ▼
 DatasetGenerator
  - 5 tipi di dato: factual, codegen, explain, bugfix, theory
  - 2 lingue: italiano, inglese
  - 3 livelli qualità: standard, high (autocritica), expert (revisione multi-round)
       │
       ▼
 distill_dataset.jsonl
       │
       ▼
  TrainLoRA (pipeline/train_lora.py)
   - LoRA su Qwen2.5-Coder-1.5B-Instruct
   - Validation split automatico 10%
   - Early stopping con load_best_model_at_end
   - Max seq length: 2048 (configurabile fino a 4096)
        │
        ▼
  Caricamento dinamico in Chat (Applica LoRA)
   - `ModelBackend.load_lora(path)` / `unload_lora()`
   - Modalità: Base / RAG / LoRA / RAG+LoRA
```

### 6.2 Teacher Backends

| Backend | API Key | Modello Default | Costo |
|---------|---------|-----------------|-------|
| opencode | No | big-pickle | 0 |
| groq | Sì (gratuita) | mixtral-8x7b-32768 | Gratuito |
| openrouter | Sì | gpt-4o | A consumo |
| ollama | No | llama3 | 0 (locale) |
| huggingface | Sì | mistralai/Mixtral-8x7B-Instruct-v0.1 | Gratuito/Pro |

### 6.3 Dataset Types

| Tipo | Descrizione | Esempio |
|------|-------------|---------|
| factual | Domanda/risposta basata su fatto documentato | "What is the address of VIC-II sprite 0 X coordinate?" |
| codegen | Generazione codice da descrizione | "Write a routine to set up a raster interrupt" |
| explain | Spiegazione di codice Assembly | "Explain what `LDA $D012` does" |
| bugfix | Correzione di codice con bug | "Fix the sprite position code (off-by-one)" |
| theory | Spiegazione di concetti | "Explain zero-page addressing in 6502" |

### 6.4 Training LoRA

Il training (pipeline/train_lora.py) si adatta automaticamente a CPU o GPU:

#### CPU (default per ambiente senza GPU)
- **Modello base**: Qwen/Qwen2.5-Coder-0.5B-Instruct (pre-downloadato nell'immagine Docker)
- **LoRA**: r=16, alpha=32, target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- **Max length**: 512 token (clampato automaticamente se la UI passa valori > 512 su CPU)
- **Batch**: per_device_train_batch_size=1, gradient_accumulation_steps=2
- **Learning rate**: 1e-4 (ridotto per stabilità su dataset piccolo)
- **Gradient clipping**: max_grad_norm=1.0
- **Evaluation**: disabilitato su CPU (`eval_strategy="no"`, `save_strategy="no"`) per velocità
- **Output**: checkpoint LoRA salvati in `data/models/c64-lora-pro/`

#### GPU (se CUDA disponibile)
- **Modello base**: Qwen/Qwen2.5-Coder-1.5B-Instruct
- **Max length**: 2048 token (configurabile in UI fino a 4096)
- **Batch**: per_device_train_batch_size=2, gradient_accumulation_steps=2
- **Learning rate**: 2e-4
- **Evaluation**: abilitato con validation split 20%

### 6.5 Profili di Configurazione

Il sistema a profili consente di salvare e ripristinare configurazioni complete di distillazione.

#### Architettura

- **6 profili predefiniti** hardcoded in `PREDEFINED_DISTILL_PROFILES` in `agent/agent_pro.py`
- **Profili personalizzati** salvati in `config/distill_profiles.json` (JSON, UTF-8)
- I profili personalizzati hanno priorità su quelli predefiniti in caso di omonimia
- Le API key **non** vengono mai salvate nei profili per sicurezza
- La funzione `get_all_profile_names()` restituisce la lista completa (predefiniti + personalizzati, deduplicata)

#### Flusso UI

1. L'utente seleziona un profilo dal dropdown `profile_dropdown`
2. L'evento `.change()` chiama `on_distill_load_profile()` che restituisce tutti i parametri
3. I parametri popolano automaticamente i controlli UI (backend, modello, tipi, lingue, slider, checkbox)
4. L'utente può modificare manualmente i parametri e salvare come nuovo profilo con `on_distill_save_profile()`
5. L'eliminazione è gestita da `on_distill_delete_profile()` (bloccata per i profili predefiniti)

#### Funzioni chiave

| Funzione | Ruolo |
|----------|-------|
| `load_user_distill_profiles()` | Carica profili personalizzati da `config/distill_profiles.json` |
| `save_user_distill_profiles(profiles)` | Salva profili personalizzati su disco |
| `get_distill_profile(name)` | Cerca in personalizzati, poi in predefiniti |
| `get_all_profile_names()` | Lista nomi deduplicata (predefiniti + personalizzati) |
| `on_distill_load_profile(name)` | Restituisce parametri del profilo per popolare la UI |
| `on_distill_save_profile(...)` | Salva configurazione corrente come nuovo profilo |
| `on_distill_delete_profile(name)` | Elimina profilo personalizzato (predefiniti protetti) |

---

## 7. Evoluzione e Roadmap

Il progetto mira a diventare un ambiente di sviluppo retrocomputing completo con:
- **Multi-step Reasoning**: Scomposizione di task complessi (es. "scrivi un intero gioco") in sotto-task gestiti sequenzialmente.
- **Symbolic Linter**: Analisi approfondita dei simboli Assembly e delle aree di memoria riservate dal KERNAL.
- **Integrazione IDE**: Possibilità di esportare direttamente file `.prg` pronti per l'emulatore.

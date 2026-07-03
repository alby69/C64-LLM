# Flusso dei Dati — Situazione attuale

```
                           ┌─────────────────────────────────────────────────────────────────────────────────────┐
                           │                                   INPUT                                            │
                           │  .pdf │ .d64 │ .g64 │ .prg │ Archive.org │ Sito web │ URL singolo │ Note .md        │
                           └────┬──────────────────────────┬──────────────────────────────────────────────────────┘
                                │                          │
                    ┌───────────┴───────────┐              │
                    ▼                       ▼              │
           ┌─────────────────┐    ┌────────────────────┐   │
           │ Estrattori disco│    │  scrape_docs.py    │   │
           │ e PRG           │    │  (PDF da sito)     │   │
           │                 │    └────────┬───────────┘   │
           │ extract_d64.py  │             │              │
           │ extract_g64.py  │             ▼              │
           │ extract_prg.py  │    ┌────────────────────┐  │  ┌────────────────────────┐
           └────────┬────────┘    │   pdf2marker.py      │  │  │  c64_asm_scraper.py    │
                    │             │  (.md + .txt +     │  │  │  scrape_url.py         │
                    ▼             └────────┬───────────┘  │  │  (codice asm)           │
           ┌─────────────────┐             │              │  └───────────┬────────────┘
           │ data/raw/     │             ▼              │              │
           │ <item_id>/      │    ┌────────────────────┐  │              ▼
           │  *.bas.txt      │    │  text_cleaner      │  │    ┌──────────────────┐
           │  *.ml.txt       │    │  (pulizia)         │  │    │  data/raw/       │
           │  *.pdf          │    └────────┬───────────┘  │    │  (file .asm)     │
           └────────┬────────┘             │              │    └────────┬─────────┘
                    │                      ▼              │              │
                    │             ┌─────────────────────────────────────────────────────┐
                    │             │         TESTO PULITO (clean.txt)                    │
                    │             └──────┬───────────────────────────────┬───────────────┘
                    │                     │                              │
                    ▼                     ▼                              ▼
           ┌─────────────────┐  ┌──────────────────────┐    ┌─────────────────────┐
           │  data/kb/manuali │  │  build_dataset       │    │ data/kb/manuali/     │
           │  .py            │  │  (QA pairs)          │    │ (file .md con       │
            │  carica .bas.txt│  └────────┬─────────────┘    │  frontmatter)       │
            │  .ml.txt .md    │           │                  │  + tutorial BASIC   │
             │  .asm .clean.txt│           ▼                  └──────────┬──────────┘
             │  (filtrato)     │           │                           │
           └────────┬────────┘  ┌──────────────────────┐              │
                    │           │ dataset_unified      │              │
                    │           │  .jsonl              │              │
                    │           │ (per training)       │              │
                    │           └──────────┬───────────┘              │
                    │                      │                           │
                    ▼                      ▼                           ▼
           ┌──────────────────────────────────────────────────────────────────────┐
           │                    INDICE VETTORIALE FAISS                            │
           │                    data/db/faiss/                                  │
           └──────────────────────────────────┬───────────────────────────────────┘
                                               │
                                               ▼
                                     ┌──────────────────────────┐
                                     │  RAG in chat              │
                                     │  (prompt + contesto KB)   │
                                     │  → risposta LLM           │
                                     └──────────────────────────┘
```

## Legenda

| Passaggio | Descrizione | Output |
|-----------|-------------|--------|
| **extract_d64.py** | Legge un D64, elenca directory, estrae PRG, detokenizza BASIC v2 | `data/raw/<item_id>/<nome>.bas.txt` |
| **extract_g64.py** | Legge un G64, decodifica GCR, ricostruisce directory, estrae PRG | `data/raw/<item_id>/<nome>.bas.txt`, `*.ml.txt` |
| **extract_prg.py** | Legge un PRG, tenta detokenize BASIC, produce hex dump per ML | `data/raw/<nome>.bas.txt`, `*.ml.txt` |
| **basic_tokens.py** | Modulo condiviso: tabella token BASIC v2 + detokenize + hex_dump + is_basic_prg | (libreria) |
| **scrape_docs.py** | Scansiona un sito, scarica PDF (segue link, evita duplicati) | `data/raw/<sito>/` |
| **c64_asm_scraper.py** | Scraping mirato su siti noti (codebase64, 6502.org, etc.) | `data/raw/<sito>/` |
| **scrape_url.py** | Scrapa un URL singolo per codice assembly | `data/raw/web/` |
| **pdf2marker.py** | Converte PDF: marker-pdf (se installato) → `.md` + `.txt` + `.meta.json`; fallback PyMuPDF → solo `.txt` | `data/kb/*.md`, `*.txt`, `*.meta.json` |
| **text_cleaner.py** | Pulisce il testo (rimuove header/footer/rumore) | `data/kb/clean.txt` |
| **build_dataset.py** | Genera coppie Q/A dal testo pulito | `data/kb/dataset_unified.jsonl` |
| **data/kb/manuali.py** | Costruisce indice FAISS da `.md` (data/kb/manuali + marker) + `.bas.txt` + `.ml.txt` + `.asm` + `data/kb/*_clean.txt` (filtrato: ≥15 keyword tecniche, >1KB, esclusi falsi `.asm`). Marker `.md` ha source_boost=1.2, `_clean.txt` ha boost=0.3 | `data/db/faiss/` |
| **estrazione EPUB** | `_extract_epub_text()` in `agent_pro.py`: decompone ZIP EPUB, estrae testo da XHTML/HTML con `HTMLParser` stdlib; fallback a `pandoc` | `data/kb/raw.txt` |
| **estrazione HTML** | `_extract_html_text()` in `agent_pro.py`: pulisce tag HTML con `HTMLParser` stdlib, ignora script/style | `data/kb/raw.txt` |
| **Google Drive** | `download_and_integrate()` enumera file con `gdown.download_folder(skip_download=True)`, poi scarica file per file. Fallback su `requests` diretto via `uc?id=` quando gdown fallisce per rate limiting. Ritardo 1.5s tra file. | `data/raw/drive_<id>/` |
| **Auto-elabora link dalla chat** | Spunta "Auto-elabora link" nella Chat: estrae URL da messaggio e risposta, aggiunge a `custom_sites.json`, avvia `download_and_integrate()` per ogni URL | Aggiunge siti + pipeline completa |
| **Chunking** | `RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)` con separatori `["\n\n", "\n", ".", " ", ""]` | `data/db/faiss/` |
| **prompts/prompts.yaml** | Template prompt per researcher, coder, orchestrator, crawler | (config) |
| **config/agent_config.yaml** | Config agente: tentativi, temperatura, RAG parametri | (config) |

## Flussi tipici

### Scarica e integra (tab "Scarica" della UI)

```
PDF diretto  (.pdf)       → download + pipeline + rebuild KB
D64 diretto  (.d64)       → download + extract_d64.py + rebuild KB
G64 diretto  (.g64)       → download + extract_g64.py + rebuild KB
PRG diretto  (.prg)       → download + extract_prg.py + rebuild KB
Archive.org  (dettaglio)   → metadata API → D64 + G64 + PRG + BEST_TEXT
                              ├── D64 → extract_d64.py
                              ├── G64 → extract_g64.py
                              ├── PRG → extract_prg.py
                              └── BEST_TEXT: seleziona il miglior formato
                                   disponibile tra TXT > EPUB > HTML > PDF
                                   ├── .txt → copia diretto → text_cleaner
                                   ├── .epub → estrazione testo (stdlib) → text_cleaner
                                   ├── .html → estrazione testo (stdlib) → text_cleaner
                                    └── .pdf → pdf2marker (.md/.txt/.meta.json) → text_cleaner (su .txt)
                                → build_dataset → rebuild KB
Altro URL    (sito web)    → scrape_docs.py (PDF) + scrape_url.py (ASM)
                           → + extract per ogni D64/G64/PRG trovato
                           → pipeline per ogni PDF → rebuild KB
```

### Scraping batch (tab "Siti" della UI)

```
Selezione checkbox siti predefiniti/personalizzati
  ├── siti predefiniti → c64_asm_scraper.py --sites <nome>
  └── siti personalizzati → scrape_url.py "<url>" "<nome>"
→ rebuild KB automatico
```

### Solo training

```
PDF in data/raw/ → docker compose run c64-pipeline
                   → docker compose up c64-train
```

## Interfaccia UI (agent/agent_pro.py)

| Tab | Funzioni |
|-----|----------|
| **Chat** | Interfaccia conversazionale con RAG toggle, Prompt Library, self-healing slider, **Technical Terms** (nuvola di tag navigabile con ricerca, clic per inserire termine nella chat), **Auto-elabora link** (estrae URL da chat, aggiunge siti, avvia pipeline) |
| **Scarica e Siti** | Download URL unico (PDF/D64/G64/PRG/Archive.org/Google Drive/sito web) con Pausa/Riprendi/Annulla; CheckboxGroup siti predefiniti (7) + personalizzati; form per aggiungere/rimuovere siti; Scrapa Selezionati |
| **Knowledge Base** | Ricostruisci Indice KB, **Esplora file KB** (elenco file con dimensioni + cerca + anteprima) |
| **Dati** | **Dataset viewer** con paginazione (◀/▶, 20 righe), ricerca case-insensitive, visualizzazione a card orizzontali con scroll; **Statistiche** |

### Tab Dati — Esplora file KB

Pulsante **Elenca tutti i file**: mostra ricorsivamente tutti i file in:
- `data/kb/manuali/` — file `.md` con frontmatter (tutorial, documentazione)
- `data/raw/` — file estratti `.bas.txt`, `.ml.txt`, `.pdf`
- `data/raw/` — file scraper `.asm`

**Cerca file** (Textbox + pulsante): filtra i file per nome (case-insensitive) per verificare
se un file è già presente nella KB. Mostra risultati raggruppati per directory con conteggio e dimensioni.

Dropdown **Anteprima file** + **Visualizza**: mostra le prime 50 righe del file selezionato.

## Controllo processo

`ProcessControl` in `agent_pro.py`:
- **Pausa**: `threading.Event` + `SIGSTOP` sul subprocess
- **Riprendi**: `SIGCONT` sul subprocess + evento settato
- **Annulla**: `killpg()` sul gruppo processo

## System Prompt (prompts/prompts.yaml)

Il prompt di sistema per il coder (`coder.base.system`) è stato rafforzato per prevenire allucinazioni:
- Elenca esplicitamente i comandi BASIC V2 validi (PRINT, INPUT, POKE, GOTO, etc.)
- Vieta comandi inesistenti (MOV, ADD, SUB, CINV, ORG, DB, etc.)
- Istruisce il modello a usare ESCLUSIVAMENTE il contesto RAG fornito
- Include anche sintassi di riferimento per Assembly 6502 (ACME)

## Bug fix: backend model GGUF

- `researcher.py` / `coder.py`: usano `hasattr(model, 'generate')` (duck typing) invece di `isinstance(model, ModelBackend)`.
- Con GGUF il backend è `LlamaCppBackend` (ha `generate()` ma non è `ModelBackend`), quindi veniva wrappato in `ModelBackend(model, tokenizer=None)` causando `'NoneType' object is not callable`.

## Note

- La **KB** (indice FAISS) serve solo per la **ricerca RAG durante la chat**. Non influisce sul modello.
- Il **training LoRA** usa `distill_dataset.jsonl` (non `dataset_unified.jsonl`), non la KB.
- I file `data/kb/*_clean.txt` (estrazioni OCR da PDF) sono ora inclusi nell'indice FAISS con filtro keyword (≥15 termini tecnici C64, >1KB) — risolve le allucinazioni filtrando solo testi OCR di qualità sufficiente. Imposta `SKIP_PDF=1` per escluderli. I `.md` curati in `data/kb/manuali/` rimangono la fonte principale.
- `extract_g64.py` usa decodifica GCR nibble-to-nibble, supporta immagini G64 standard a 35-40 tracce.
- `extract_prg.py` riconosce automaticamente BASIC (detokenize) vs ML (hex dump).
- I file `.bas.txt` e `.ml.txt` vengono automaticamente inclusi nell'indice FAISS.
- I siti personalizzati vengono persisti in `data/custom_sites.json` (sopravvive ai riavvii container).
- Per i siti personalizzati, lo scraping esegue prima `scrape_docs.py` (cerca PDF) e poi `scrape_url.py` (cerca codice Assembly).
- `scrape_docs.py` usa `cloudscraper` per bypassare la protezione Cloudflare su siti come ready64.org.
- `archive.org/download/...` usa `verify=False` per evitare problemi SSL in ambiente Docker.
- Ogni download da Archive.org è wrappato in `try/except` con `continue`: se un file singolo fallisce (es. 500 Server Error), viene loggato e si passa al successivo — non blocca l'intera operazione.
- Archive.org seleziona automaticamente il miglior formato disponibile per la KB: TXT > EPUB > HTML > PDF. Scarica un solo file invece di tutti i PDF.
- Google Drive: download file-per-file con `gdown.download()`, fallback su `requests` diretto se gdown fallisce (rate limiting). Delay 1.5s tra file.
- `n_ctx` in `LlamaCppBackend` portato da 2048 a 8192 per gestire messaggi lunghi (es. risposte Claude/ChatGPT nella chat).
- Lo splitter della KB è passato da `CharacterTextSplitter(chunk_size=500)` a `RecursiveCharacterTextSplitter(chunk_size=1500, overlap=150)` con separatori multilivello.
- Le letture file nella KB usano `encoding="utf-8", errors="replace"` e `SKIP_EXTS` per saltare file binari (`.gz`, `.zip`, `.pdf`, `.d64`, ecc.).
- Il dataset viewer nel tab Dati usa `gr.HTML` con card in flexbox orizzontale + scroll, paginazione 20 entry e ricerca case-insensitive.


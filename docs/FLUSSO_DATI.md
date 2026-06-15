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
           └────────┬────────┘    │   pdf2text.py      │  │  │  c64_asm_scraper.py    │
                    │             │  (estrazione)       │  │  │  scrape_url.py         │
                    ▼             └────────┬───────────┘  │  │  (codice asm)           │
           ┌─────────────────┐             │              │  └───────────┬────────────┘
           │ data/input/     │             ▼              │              │
           │ <item_id>/      │    ┌────────────────────┐  │              ▼
           │  *.bas.txt      │    │  text_cleaner      │  │    ┌──────────────────┐
           │  *.ml.txt       │    │  (pulizia)         │  │    │  data/src/       │
           │  *.pdf          │    └────────┬───────────┘  │    │  (file .asm)     │
           └────────┬────────┘             │              │    └────────┬─────────┘
                    │                      ▼              │              │
                    │             ┌─────────────────────────────────────────────────────┐
                    │             │         TESTO PULITO (clean.txt)                    │
                    │             └──────┬───────────────────────────────┬───────────────┘
                    │                     │                              │
                    ▼                     ▼                              ▼
           ┌─────────────────┐  ┌──────────────────────┐    ┌─────────────────────┐
           │  knowledge_base │  │  build_dataset       │    │ knowledge_base/     │
           │  .py            │  │  (QA pairs)          │    │ (file .md con       │
           │  carica .bas.txt│  └────────┬─────────────┘    │  frontmatter)       │
           │  .ml.txt .md    │           │                  │  + tutorial BASIC   │
           │  e clean.txt    │           ▼                  └──────────┬──────────┘
           └────────┬────────┘  ┌──────────────────────┐              │
                    │           │ dataset_unified      │              │
                    │           │  .jsonl              │              │
                    │           │ (per training)       │              │
                    │           └──────────┬───────────┘              │
                    │                      │                           │
                    ▼                      ▼                           ▼
           ┌──────────────────────────────────────────────────────────────────────┐
           │                    INDICE VETTORIALE FAISS                            │
           │                    data/vectorstore/                                  │
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
| **extract_d64.py** | Legge un D64, elenca directory, estrae PRG, detokenizza BASIC v2 | `data/input/<item_id>/<nome>.bas.txt` |
| **extract_g64.py** | Legge un G64, decodifica GCR, ricostruisce directory, estrae PRG | `data/input/<item_id>/<nome>.bas.txt`, `*.ml.txt` |
| **extract_prg.py** | Legge un PRG, tenta detokenize BASIC, produce hex dump per ML | `data/input/<nome>.bas.txt`, `*.ml.txt` |
| **basic_tokens.py** | Modulo condiviso: tabella token BASIC v2 + detokenize + hex_dump + is_basic_prg | (libreria) |
| **scrape_docs.py** | Scansiona un sito, scarica PDF (segue link, evita duplicati) | `data/input/<sito>/` |
| **c64_asm_scraper.py** | Scraping mirato su siti noti (codebase64, 6502.org, etc.) | `data/src/<sito>/` |
| **scrape_url.py** | Scrapa un URL singolo per codice assembly | `data/src/web/` |
| **pdf2text.py** | Estrae testo grezzo da PDF | `data/output/raw.txt` |
| **text_cleaner.py** | Pulisce il testo (rimuove header/footer/rumore) | `data/output/clean.txt` |
| **build_dataset.py** | Genera coppie Q/A dal testo pulito | `data/output/dataset_unified.jsonl` |
| **knowledge_base.py** | Costruisce indice FAISS da `.md` + `clean.txt` + `.bas.txt` + `.ml.txt` | `data/vectorstore/` |
| **prompts/prompts.yaml** | Template prompt per researcher, coder, orchestrator, crawler | (config) |
| **config/agent_config.yaml** | Config agente: tentativi, temperatura, RAG parametri | (config) |

## Flussi tipici

### Scarica e integra (tab "Scarica" della UI)

```
PDF diretto  (.pdf)       → download + pipeline + rebuild KB
D64 diretto  (.d64)       → download + extract_d64.py + rebuild KB
G64 diretto  (.g64)       → download + extract_g64.py + rebuild KB
PRG diretto  (.prg)       → download + extract_prg.py + rebuild KB
Archive.org  (dettaglio)   → metadata API → D64 + G64 + PRG + PDF
                              ├── D64 → extract_d64.py
                              ├── G64 → extract_g64.py
                              ├── PRG → extract_prg.py
                              └── PDF (max 5) → pipeline
                           → rebuild KB
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
PDF in data/input/ → docker compose run c64-pipeline
                   → docker compose up c64-train
```

## Interfaccia UI (agent/agent_pro.py)

| Tab | Funzioni |
|-----|----------|
| **Chat** | Interfaccia conversazionale con RAG toggle, Prompt Library, self-healing slider |
| **Scarica** | URL input + Avvia / Pausa (SIGSTOP) / Riprendi (SIGCONT) / Annulla. Supporta PDF, D64, G64, PRG, Archive.org |
| **Siti** | CheckboxGroup siti predefiniti (7) + personalizzati (da `data/custom_sites.json`); form per aggiungere nuovi siti |
| **Dati** | Ricostruisci KB, Visualizza Dataset, Statistiche, **Esplora file KB** (elenco file con dimensioni + anteprima) |

### Tab Dati — Esplora file KB

Pulsante **Elenca tutti i file**: mostra ricorsivamente tutti i file in:
- `knowledge_base/` — file `.md` con frontmatter (tutorial, documentazione)
- `data/input/` — file estratti `.bas.txt`, `.ml.txt`, `.pdf`
- `data/src/` — file scraper `.asm`

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
- Il **training LoRA** usa solo `dataset_unified.jsonl`, non la KB.
- `extract_g64.py` usa decodifica GCR nibble-to-nibble, supporta immagini G64 standard a 35-40 tracce.
- `extract_prg.py` riconosce automaticamente BASIC (detokenize) vs ML (hex dump).
- I file `.bas.txt` e `.ml.txt` vengono automaticamente inclusi nell'indice FAISS.
- I siti personalizzati vengono persisti in `data/custom_sites.json` (sopravvive ai riavvii container).
- `archive.org/download/...` usa `verify=False` per evitare problemi SSL in ambiente Docker.

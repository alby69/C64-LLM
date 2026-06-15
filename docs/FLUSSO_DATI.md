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
           │  .ml.txt .md    │           │                  └──────────┬──────────┘
           │  e clean.txt    │           ▼                            │
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
                                    │  (cerca documenti)        │
                                    │  + risposta con LLM       │
                                    └──────────────────────────┘
```

## Legenda

| Passaggio | Descrizione | Output |
|-----------|-------------|--------|
| **extract_d64.py** | Legge un D64, elenca directory, estrae PRG, detokenizza BASIC v2 | `data/input/<item_id>/<nome>.bas.txt` |
| **extract_g64.py** | Legge un G64, decodifica GCR, ricostruisce directory, estrae PRG | `data/input/<item_id>/<nome>.bas.txt`, `*.ml.txt` |
| **extract_prg.py** | Legge un PRG, tenta detokenize BASIC, produce hex dump per ML | `data/input/<nome>.bas.txt`, `*.ml.txt` |
| **scrape_docs.py** | Scansiona un sito, scarica PDF (segue link, evita duplicati) | `data/input/<sito>/` |
| **c64_asm_scraper.py** | Scraping mirato su siti noti (codebase64, 6502.org, etc.) | `data/src/<sito>/` |
| **scrape_url.py** | Scrapa un URL singolo per codice assembly | `data/src/web/` |
| **pdf2text.py** | Estrae testo grezzo da PDF | `data/output/raw.txt` |
| **text_cleaner.py** | Pulisce il testo (rimuove header/footer/rumore) | `data/output/clean.txt` |
| **build_dataset.py** | Genera coppie Q/A dal testo pulito | `data/output/dataset_unified.jsonl` |
| **knowledge_base.py** | Costruisce indice FAISS da `.md` + `clean.txt` + `.bas.txt` + `.ml.txt` | `data/vectorstore/` |
| **basic_tokens.py** | Modulo condiviso: tabella token BASIC v2 + funzioni detokenize/hex_dump | (libreria) |

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
| **Scarica** | URL input + Avvia / Pausa (SIGSTOP) / Riprendi (SIGCONT) / Annulla |
| **Siti** | CheckboxGroup siti predefiniti (7) + personalizzati (da `data/custom_sites.json`); form per aggiungere nuovi siti |
| **Dati** | Ricostruisci KB / Visualizza Dataset / Statistiche (conteggi file, entries) |

## Controllo processo

`ProcessControl` in `agent_pro.py`:
- **Pausa**: `threading.Event` + `SIGSTOP` sul subprocess
- **Riprendi**: `SIGCONT` sul subprocess + evento settato
- **Annulla**: `killpg()` sul gruppo processo

## Note

- La **KB** (indice FAISS) serve solo per la **ricerca RAG durante la chat**. Non influisce sul modello.
- Il **training LoRA** usa solo `dataset_unified.jsonl`, non la KB.
- `extract_g64.py` usa decodifica GCR nibble-to-nibble, supporta immagini G64 standard a 35-40 tracce.
- `extract_prg.py` riconosce automaticamente BASIC (detokenize) vs ML (hex dump).
- I file `.bas.txt` e `.ml.txt` vengono automaticamente inclusi nell'indice FAISS.
- I siti personalizzati vengono persisti in `data/custom_sites.json` (sopravvive ai riavvii container).
- `archive.org/download/...` usa `verify=False` per evitare problemi SSL in ambiente Docker.

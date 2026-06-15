# Flusso dei Dati — Situazione attuale

```
                           ┌─────────────────────────────────────────────────────────────────────┐
                           │                           INPUT                                     │
                           │  PDF .d64 │ Archive.org │ Sito web │ URL singolo │ Note .md          │
                           └────┬───────────────────────┬─────────────────────────────────────────┘
                                │                       │
                    ┌───────────┴───────────┐           │
                    ▼                       ▼           │
           ┌─────────────────┐    ┌──────────────────┐  │
           │ extract_d64.py  │    │  scrape_docs.py   │  │
           │ (D64 → BASIC)   │    │  (PDF da sito)    │  │
           └────────┬────────┘    └────────┬─────────┘  │
                    │                      │             │
                    ▼                      ▼             │
           ┌─────────────────┐   ┌──────────────────┐   │
           │ data/input/     │   │  data/input/      │   │
           │ <item_id>/*.bas │   │  <sito>/*.pdf     │   │
           │        .txt     │   └────────┬─────────┘   │
           └────────┬────────┘            │             │
                    │                     ▼             │
                    │             ┌──────────────────┐  │  ┌──────────────────────┐
                    │             │   pdf2text.py     │  │  │  c64_asm_scraper.py │
                    │             │  (estrazione)     │  │  │  scrape_url.py      │
                    │             └────────┬─────────┘  │  │  (codice asm)        │
                    │                      │             │  └──────────┬───────────┘
                    │                      ▼             │             │
                    │             ┌──────────────────┐  │             ▼
                    │             │  text_cleaner     │  │   ┌─────────────────┐
                    │             │  (pulizia)        │  │   │  data/src/       │
                    │             └────────┬─────────┘  │   │  (file .asm)     │
                    │                      │             │   └────────┬────────┘
                    │                      ▼             │             │
                    │             ┌────────────────────────────────────────────┐
                    │             │         TESTO PULITO (clean.txt)           │
                    │             └──────┬──────────────────────────┬──────────┘
                    │                     │                         │
                    ▼                     ▼                         ▼
           ┌─────────────────┐  ┌──────────────────┐    ┌──────────────────┐
           │  knowledge_base │  │  build_dataset    │    │ knowledge_base/  │
           │  .py            │  │  (QA pairs)       │    │ (file .md con    │
           │  carica .bas.txt│  └────────┬─────────┘    │  frontmatter)    │
           │  .md e clean.txt│           │               └────────┬─────────┘
           └────────┬────────┘           ▼                        │
                    │           ┌──────────────────┐               │
                    │           │ dataset_unified  │               │
                    │           │  .jsonl          │               │
                    │           │ (per training)   │               │
                    │           └────────┬─────────┘               │
                    │                    │                          │
                    ▼                    ▼                          ▼
           ┌─────────────────────────────────────────────────────────────────┐
           │                    INDICE VETTORIALE FAISS                       │
           │                    data/vectorstore/                             │
           └──────────────────────────────┬──────────────────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────────┐
                                │  RAG in chat          │
                                │  (cerca documenti)    │
                                │  + risposta con LLM   │
                                └──────────────────────┘
```

## Legenda

| Passaggio | Descrizione | Output |
|-----------|-------------|--------|
| **extract_d64.py** | Legge un D64, estrae PRG, detokenizza BASIC v2 | `data/input/<item_id>/<nome>.bas.txt` |
| **scrape_docs.py** | Scansiona un sito, scarica PDF (segue link, evita duplicati) | `data/input/<sito>/` |
| **c64_asm_scraper.py** | Scraping mirato su siti noti (codebase64, 6502.org, etc.) | `data/src/<sito>/` |
| **scrape_url.py** | Scrapa un URL singolo per codice assembly | `data/src/web/` |
| **pdf2text.py** | Estrae testo grezzo da PDF | `data/output/raw.txt` |
| **text_cleaner.py** | Pulisce il testo (rimuove header/footer/rumore) | `data/output/clean.txt` |
| **build_dataset.py** | Genera coppie Q/A dal testo pulito | `data/output/dataset_unified.jsonl` |
| **knowledge_base.py** | Costruisce indice FAISS da `.md` + `clean.txt` + `.bas.txt` | `data/vectorstore/` |
| **train_lora.py** | Addestra LoRA su dataset | `data/models/c64-lora-pro/` |

## Flussi tipici

### Scarica e integra (tab "Scarica" della UI)

```
PDF diretto  (.pdf)       → download + pipeline + rebuild KB
D64 diretto  (.d64)       → download + extract_d64.py + rebuild KB
Archive.org  (dettaglio)   → metadata API → D64 e PDF separati
                              ├── D64 → extract_d64.py
                              └── PDF (max 5) → pipeline
                           → rebuild KB
Altro URL    (sito web)    → scrape_docs.py (PDF) + scrape_url.py (ASM)
                           → pipeline per ogni PDF trovato → rebuild KB
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

### Completo (KB + training)

```
URL → Scarica e Integra Subito → KB aggiornata
Poi: docker compose up c64-train
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
- I file `.bas.txt` estratti da D64 vengono automaticamente inclusi nell'indice FAISS.
- I siti personalizzati vengono persisti in `data/custom_sites.json` (sopravvive ai riavvii container).
- `archive.org/download/...` usa `verify=False` per evitare problemi SSL in ambiente Docker.

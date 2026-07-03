# Nuova Struttura Dati Semplificata

Per ridurre la complessità e il debito tecnico, il progetto passerà a una struttura dati minimalista e centralizzata.

## 1. Struttura Proposta

```text
data/
├── raw/                # SORGENTI GREZZE (Read-only per il RAG)
│   ├── pdf/            # Documenti originali scaricati
│   ├── disks/          # Immagini D64, G64
│   ├── programs/       # File .PRG originali
│   └── web/            # Codice ASM scaricato e file temporanei
├── kb/                 # KNOWLEDGE BASE (Markdown pronto per RAG)
│   ├── manuali/        # Manuali curati (ex data/kb/manuali/)
│   ├── tutorial/       # Tutorial BASIC/ASM
│   └── scraped/        # Output di Scrapy e Marker (ex data/kb/)
├── db/                 # STATO E INDICI
│   ├── faiss/          # Indice vettoriale
│   ├── metadata.db     # SQLite per tracciare file e hash
│   └── crawler_status/ # Log di aggiornamento sorgenti
└── models/             # INTELLIGENZA ARTIFICIALE
    ├── base/           # Modelli GGUF/HF
    └── adapters/       # LoRA Fine-tuning
```

## 2. Benefici della Riorganizzazione

1.  **Dati Originali vs Elaborati**: Separazione netta tra `raw/` (immutabile) e `kb/` (derivato).
2.  **Unificazione KB**: Tutti i file indicizzabili dal RAG risiedono in `kb/`. Non serve più cercare in `input/`, `output/`, `src/` e `data/kb/manuali/`.
3.  **Gestione dei Duplicati**: Il file `metadata.db` centralizzerà il tracking degli hash, rendendo obsoleti i file `.json` sparsi per il progetto.
4.  **Facilità di Backup**: Basta salvare `data/kb/` e `data/raw/` per avere l'intero patrimonio informativo.

## 3. Tabella di Migrazione

| Vecchia Cartella | Nuova Destinazione |
|------------------|--------------------|
| `data/raw/`    | `data/raw/` (suddivisa per tipo) |
| `data/kb/`   | `data/kb/scraped/` |
| `data/raw/`      | `data/raw/web/` |
| `data/raw/.tmp/`      | (Eliminata - usa `.tmp` in `raw/`) |
| `data/db/faiss/` | `data/db/faiss/` |
| `data/kb/manuali/` | `data/kb/manuali/` |
| `config/crawler_status.json` | `data/db/crawler_status/status.json` |

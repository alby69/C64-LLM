---
title: "Commodore 64 Programmer's Reference Guide - Knowledge Base"
description: "Knowledge base estratta dal manuale ufficiale Commodore 64 Programmer's Reference Guide per alimentare il progetto C64-LLM"
tags: [c64, commodore-64, knowledge-base, reference, programming]
source: "Commodore 64 Programmer's Reference Guide (1982-1983)"
project: "https://github.com/alby69/C64-LLM"
---

# Commodore 64 Programmer's Reference Guide - Knowledge Base

Questa knowledge base è stata estratta dal manuale ufficiale **Commodore 64 Programmer's Reference Guide** (Prima Edizione, Ottava Ristampa 1983) per alimentare il progetto [C64-LLM](https://github.com/alby69/C64-LLM).

## Struttura della Knowledge Base

| Cartella | Contenuto |
|----------|-----------|
| `00-intro/` | Introduzione e panoramica del manuale |
| `01-basic-programming/` | Regole di programmazione BASIC |
| `02-basic-vocabulary/` | Vocabolario completo BASIC |
| `03-graphics/` | Programmazione grafica e sprite |
| `04-sound-music/` | Programmazione audio e SID |
| `05-machine-language/` | Linguaggio macchina 6502 e KERNAL |
| `06-io-guide/` | Guida Input/Output e periferiche |
| `07-appendices/` | Appendici tecniche e riferimenti |
| `08-quick-reference/` | Scheda di riferimento rapido |

## Come usare questa KB nel progetto C64-LLM

1. Copiare i file `.md` nella directory `knowledge_base/` o `data/input/` del progetto
2. Eseguire la pipeline di indicizzazione:
   ```bash
   docker compose run --rm c64-pipeline python agent/knowledge_base.py
   ```
3. I file verranno indicizzati nel sistema RAG con FAISS

## Formato dei file

Ogni file markdown include frontmatter YAML con:
- `title`: Titolo del documento
- `description`: Descrizione breve
- `tags`: Tag per la categorizzazione
- `source`: Fonte originale nel manuale

## Note sulla fonte

Questo manuale è stato prodotto in formato EPUB dall'Internet Archive tramite OCR. Alcune pagine potrebbero contenere errori di riconoscimento. Il contenuto è stato riorganizzato e strutturato per una migliore fruizione nella knowledge base.

## Licenza

Il manuale originale è © 1982 Commodore Business Machines, Inc. Questa estrazione è destinata a scopi di ricerca e preservazione storica.

---

*Knowledge base preparata per il progetto C64-LLM*

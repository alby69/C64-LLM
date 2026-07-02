# Integrazione C64-Scrapy

Questo documento descrive come sostituire l'attuale sistema di scraping di C64-LLM con il framework avanzato **C64-Scrapy**.

## 1. Motivazione

Il sistema attuale di C64-LLM utilizza script standalone (`c64_asm_scraper.py`, `scrape_docs.py`) difficili da manutenere e scalare. **C64-Scrapy** offre:
- Gestione robusta delle sessioni e dei retry.
- Pipeline di post-processing integrate per generare Markdown con frontmatter YAML.
- Architettura a spider specializzati (es. `bbcelite`, `codebase64`).
- Generazione automatica di manuali PDF tramite Pandoc.

## 2. Strategia di Sostituzione

La sostituzione avverrà tramite un adapter dedicato (`ScrapyWrapper`) nel modulo `pipeline/acquisition/`.

### 2.1 Mappatura Funzionalità

| Funzione Attuale C64-LLM | Spider C64-Scrapy Equivalente | Note |
|---------------------------|-------------------------------|------|
| `c64_asm_scraper.py`      | `codebase64.py`, `bbcelite.py`| Molto più granulare in Scrapy. |
| `scrape_url.py`           | `generic_spider` (TBD)        | Scrapy può gestire URL custom via command line. |
| `agent/crawler.py`        | N/A (Keep for Archive.org)    | Archive.org richiede API specifiche, non solo scraping. |

### 2.2 Workflow Integrato

1.  **Chiamata**: L'interfaccia utente o l'Orchestrator richiede lo scraping di un sito.
2.  **Esecuzione**: `ScrapyWrapper` lancia il comando:
    ```bash
    scrapy crawl <spider_name> -s DOCS_OUTPUT_DIR=data/raw/scrapy_output
    ```
3.  **Ingestion**: I file Markdown prodotti da Scrapy vengono spostati o linkati in `data/kb/`.
4.  **Rebuild**: C64-LLM aggiorna l'indice FAISS leggendo i nuovi file in `data/kb/`.

## 3. Modifiche al Codice

### 3.1 `pipeline/acquisition/scrapy_wrapper.py` (Nuovo)
Questo file fungerà da ponte:
```python
import subprocess
from pathlib import Path

class ScrapyWrapper:
    def __init__(self, scrapy_repo_path):
        self.repo_path = Path(scrapy_repo_path)

    def run_spider(self, spider_name, output_dir):
        cmd = [
            "scrapy", "crawl", spider_name,
            "-s", f"DOCS_OUTPUT_DIR={output_dir}"
        ]
        return subprocess.run(cmd, cwd=self.repo_path)
```

### 3.2 Dismissione Script Legacy
Una volta verificata l'integrazione, i seguenti file verranno rimossi per ridurre il debito tecnico:
- `pipeline/c64_asm_scraper.py`
- `pipeline/scrape_url.py`
- `pipeline/scrape_docs.py`

## 4. Gestione delle Dipendenze

È necessario unificare i `requirements.txt`. C64-Scrapy richiede `scrapy` e `pyyaml`, che verranno aggiunti al core di C64-LLM.

```text
# Aggiunte a core/requirements.txt
scrapy>=2.11.0
itemadapter>=0.8.0
```

## 5. Configurazione

Il file `config/crawler_sources.yaml` verrà aggiornato per mappare i nomi delle fonti agli spider di Scrapy:

```yaml
sources:
  - name: "Codebase64"
    type: "scrapy"
    spider: "codebase64"
    ...
```

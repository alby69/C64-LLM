# Piano di Implementazione per il Completamento della Roadmap e Ottimizzazione del Disaccoppiamento

Questo documento definisce la strategia dettagliata di implementazione, integrazione e disaccoppiamento per completare l'ecosistema **C64 Intelligence Ecosystem**, garantendo che **C64-LLM** rimanga snello, modulare e focalizzato unicamente sui suoi compiti primari (ragionamento multi-agente, RAG, training e UI).

---

## 1. Visione d'Insieme e Architettura Disaccoppiata

La filosofia architetturale dell'ecosistema è ispirata a principi di **massima separazione delle responsabilità (Separation of Concerns)**. Ciascun repository nel **C64-Intelligence-SDK** ha un'identità precisa e confini chiari:

```
                  ┌──────────────────────────────────────────┐
                  │          C64-Intelligence-SDK            │
                  │         (Aggregator Repository)          │
                  └────────────────────┬─────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
   ┌───────────┐                 ┌───────────┐                 ┌───────────┐
   │ C64-Scrapy│                 │C64-KB-Agent│                │   PYC64   │
   │ (Crawling │                 │(Knowledge  │                │(Diagnostic│
   │ & Scraping│                 │   Base)    │                │  & Tools) │
   └─────┬─────┘                 └─────┬─────┘                 └─────┬─────┘
         │                             │                             │
         │ (spider outputs)            │ (markdown docs)             │ (emulator tools)
         └──────────────┐              │                             │
                        ▼              ▼                             │
                  ┌──────────────────────────┐                       │
                  │         C64-LLM          │◄──────────────────────┘
                  │   (Core AI Engine, RAG,  │  (Cheshire Cat Plugin)
                  │    nanoGPT & Gradio UI)  │
                  └──────────────────────────┘
```

### Ruoli dei Componenti nell'Ecosistema
- **C64-LLM**: Il cervello centrale. Fornisce l'orchestrazione multi-agente, la pipeline di training nanoGPT (pre-training/fine-tuning), l'indicizzazione RAG con FAISS, e l'interfaccia utente Gradio (con emulatore VICE WASM integrato).
- **C64-Scrapy**: L'addetto all'acquisizione dati. Esegue crawler e spider specializzati per estrarre informazioni da siti storici, forum e archivi (es. Archive.org).
- **C64-KB-Agent**: Il custode della Knowledge Base. Standardizza e pulisce i testi, cura i manuali tecnici e detiene l'indice della Knowledge Graph.
- **PYC64**: Il set di strumenti nativi. Fornisce utility per l'analisi di formati Commodore (PRG, D64, G64, BASIC tokenization) ed espone strumenti all'agente tramite plugin.

---

## 2. Stato della Roadmap ed Evoluzione (Fasi 0-10)

Ad oggi, le fasi di evoluzione previste nella Roadmap originale sono state implementate con successo:
1. **Fasi 0-2 (Snellimento e Submoduli)**: Rimozione di codice legacy duplicato (come gli estrattori di dischi). Integrazione di `C64-KB-Agent` e `external/py6502` come submoduli.
2. **Fase 3 (nanoGPT Pipeline & Adapter)**: Sviluppo di `nanogpt_prepper.py`, `nanogpt_trainer.py` e della scheda nanoGPT in Gradio UI con log asincroni. Integrazione di `C64-Scrapy` come submodulo ufficiale e prioritizzazione dei percorsi locali in `ScrapyKBAdapter`.
3. **Fase 4-5 (Training & Fine-tuning)**: Supporto per pre-training da zero ed esecuzione di benchmark quantitativi e qualitativi via `nanogpt_eval.py`.
4. **Fase 6-7 (Custom Tokenizer & Backend)**: Implementazione del tokenizer `c64_custom` e del backend locale prioritario `NanoGPTBackend` in `model_backend.py`.
5. **Fase 8 (Multi-modal RAG)**: Creazione di `c64_graphics_extractor.py` per decodificare sprite e asset in Pillow, e indicizzazione multimodale tramite `multimodal_rag.py`.
6. **Fase 9-10 (Linter & Emulator)**: Integrazione di un editor Monaco retro con feedback linter ACME in tempo reale, autocompilazione del codice tramite `prg_builder.py` e visualizzazione interattiva nell'emulatore VICE WASM.

---

## 3. Strategia di Disaccoppiamento Avanzato

Per impedire che C64-LLM diventi un "monolito fragile" e per assicurare la manutenibilità futura, adottiamo le seguenti linee guida:

### A. Delega Rigida dell'Acquisizione
Nessuna funzione di download diretto (ad esempio chiamate a Google Drive, `gdown` o scraping HTTP raw) deve essere scritta nel core di C64-LLM.
- Tutte le richieste di download di nuovi manuali o sorgenti devono essere gestite delegandole a **C64-Scrapy** avviando gli appositi spider.
- L'ingestione avviene in modo disaccoppiato mediante il modulo `pipeline/acquisition/scrapy_kb_adapter.py`, che fa da ponte tra i subrepo.

### B. Astrazione dei Formati Binari
L'estrazione o detokenizzazione di file C64 (es. `.prg`, `.d64`, `.g64`) non viene effettuata da moduli proprietari interni a C64-LLM.
- C64-LLM chiama moduli di utility di **PYC64** o si affida all'emulatore/simulatore standardizzato.
- Questo isola C64-LLM da bug di basso livello legati alla decodifica di dischi o tracce GCR.

### C. Architettura di Testing Isolata
I test di integrazione per l'integrazione di submoduli esterni (come `ScrapyKBAdapter`) devono usare tecniche di **mocking** e **filesystem temporanei** per non dipendere dallo stato locale dei submoduli o da connessioni di rete durante la Continuous Integration.

---

## 4. Piano di Azione per il Completamento e Consolidamento

Per completare e rifinire l'ecosistema, il piano d'azione prevede tre step tecnici immediati:

### Step 1: Rafforzamento dei Test di Integrazione
**Obiettivo**: Garantire che il bridge di sincronizzazione (`ScrapyKBAdapter`) sia coperto da test automatizzati accurati per evitare regressioni nelle future release.
- Creare il file `tests/test_scrapy_kb_adapter.py`.
- Utilizzare `unittest.mock` per simulare l'ambiente di C64-Scrapy e C64-KB-Agent.
- Testare:
  - Sincronizzazione di file Markdown validi.
  - Comportamento in assenza delle directory dei submoduli (gestione elegante dei fallback).
  - Validazione dei metadati (titolo e tag inseriti o arricchiti automaticamente nel frontmatter).
  - Riconoscimento degli hash MD5 per evitare indicizzazioni e copie duplicate ridondanti.

### Step 2: Ottimizzazione del Codice dell'Adattatore
**Obiettivo**: Migliorare la resilienza dell'adattatore durante le esecuzioni notturne automatizzate (es. tramite GitHub Actions).
- Aggiornare `scrapy_kb_adapter.py` gestendo eccezioni specifiche nei parser di frontmatter e YAML.
- Assicurare che i log indichino chiaramente l'origine di eventuali fallimenti senza interrompere bruscamente l'intera pipeline di RAG.

### Step 3: Pipeline di CI/CD e Sincronizzazione Automatica
**Obiettivo**: Mantenere la Knowledge Base sempre allineata senza intervento manuale.
- Integrare il flusso di sync di `ScrapyKBAdapter` all'interno del workflow `.github/workflows/kb_sync.yml`.
- All'attivazione del workflow:
  1. Aggiorna i submoduli git (`git submodule update --remote`).
  2. Esegue il sync via `ScrapyKBAdapter`.
  3. Ricostruisce l'indice FAISS tramite `C64KnowledgeBase.build_index()`.

---

## 5. Metriche di Qualità dell'Integrazione

Per validare il successo dell'implementazione di questo piano, verranno monitorati i seguenti indicatori:
- **Zero Duplicazioni**: Nessun file di crawling o di parsing di basso livello Commodore al di fuori dei rispettivi subrepo.
- **Passaggio dei Test al 100%**: Esecuzione della suite completa di test (`pytest`) con esito positivo.
- **Integrità del Frontmatter**: Ogni documento indicizzato nel RAG deve contenere metadati standardizzati (`title` e `tags`).
- **Nessuna regressione**: Le modifiche di ottimizzazione dell'adattatore non devono inficiare la stabilità della Gradio UI.

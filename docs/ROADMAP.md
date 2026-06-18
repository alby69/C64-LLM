# Roadmap e Stato dello Sviluppo - C64 Coding Agent

Questo documento riassume lo stato attuale del progetto e definisce le prossime tappe per il miglioramento della robustezza e dell'usabilità.

## 📊 Stato Attuale

| Componente | Stato | Note |
| :--- | :--- | :--- |
| **Orchestrator** | ✅ Funzionante | Gestisce il flusso base e un round di self-healing. |
| **Researcher** | ✅ Funzionante | RAG con FAISS + filtro PDF, k=10, wiki-links. HyDE disabilitato. |
| **Coder** | ✅ Funzionante | Supporto BASIC e Assembly con CoT. |
| **Validator** | ⚠️ Parziale | ACME per ASM, Parser interno per BASIC (base). |
| **UI (Gradio)** | ✅ Funzionante | Interfaccia chat con Prompt Library. |
| **Knowledge Base** | ✅ Funzionante | Crawler proattivo e indicizzazione frontmatter. |

## 🚀 Miglioramenti Identificati

### 1. Robustezza (Core)
- [x] **Multi-round Self-Healing**: Passare da 1 a 3 tentativi di correzione automatica. (Implementato)
- [x] **Validazione BASIC Avanzata**: Rilevamento collisioni variabili (primi 2 caratteri) e warning per linee troppo lunghe. (Implementato)
- [x] **Memory Protection**: Migliorare il `MemoryMapTracker` per segnalare sovrapposizioni tra codice e vettori di sistema. (Implementato)

### 2. Usabilità (Developer Experience)
- [x] **Logging Centralizzato**: Migliore tracciabilità dei pensieri degli agenti nella UI. (Implementato con collapsible logs)
- [x] **Configurazione Unificata**: Spostare parametri (timeout, round, modelli) in un file YAML. (Implementato in `config/agent_config.yaml`)
- [x] **Use Cases Documentati**: Aggiungere esempi reali di interazione nel README. (Implementato in `docs/USE_CASES.md`)

### 3. Stabilità RAG e Robustezza (Giugno 2026)
- [x] **Knowledge Base riscritta**: Sostituito langchain FAISS + HuggingFaceEmbeddings con FAISS diretto + sentence-transformers, risolvendo OOM e incompatibilità.
- [x] **Inclusione PDF con filtro**: `data/output/*_clean.txt` ora indicizzato con filtro keyword (≥15 termini tecnici), risolvendo allucinazioni OCR.
- [x] **Rimozione HyDE**: Disabilitato (`use_hyde: false`) — peggiorava il retrieval con allucinazioni del modello 1.5B.
- [x] **k_results aumentato**: Da 3 a 10, migliorando la copertura del contesto.
- [x] **Chunking migliorato**: `chunk_size` da 500→2000 e `chunk_overlap` da 50→200 per contesto tecnico completo.
- [x] **Falsi `.asm` filtrati**: File PDF/binari rinominati come `.asm` (doppia estensione, >500KB) esclusi dall'indice.
- [x] **ACME cross-assembler**: Compilato da sorgente e integrato nella validazione.
- [x] **Prompt system rafforzato**: Regole esplicite per prevenire comandi BASIC inesistenti e allucinazioni su indirizzi.

### 4. Documentazione (Consolidamento)
- [x] **Unificazione Technical Manual**: Unificare i vari `DEEP_DIVE` in un unico manuale tecnico. (Implementato in `docs/TECHNICAL_MANUAL.md`)
- [x] **Aggiornamento README**: Inseriti link a Use Cases e Roadmap. (Completato)

---

## 🚀 Prossimi Passi (Evoluzione Futura)

- [ ] **Reranking semantico**: Migliorare la precisione del RAG con un cross-encoder.
- [ ] **HyDE (Hypothetical Document Embeddings)**: Disabilitato — il modello 1.5B generava risposte ipotetiche allucinate. Sostituito da `k_results=10` e chunk più ampi.
- [x] **Cycle Counter per Assembly**: Analisi delle performance del codice generato. (Implementato in `utils/cycle_counter.py`)

---

## 📅 Cronologia Sviluppo

- **Fase 1: Rafforzamento Agenti**: Completata (Self-healing, BASIC validation, Memory tracking).
- **Fase 2: Refactoring UI e Feedback**: Completata (Config unificata, Logs in UI).
- **Fase 3: Simulazione Use Cases**: Completata (Documentati in `docs/USE_CASES.md`).
- **Fase 4: Aggiornamento Documentazione**: Completata.
- **Fase 5: Stabilità RAG e Robustezza (Giugno 2026)**: Completata (KB riscritta, PDF inclusi con filtro, HyDE disabilitato, k=10, chunk 2000/200, falsi `.asm` esclusi, ACME integrato, prompt rafforzato).

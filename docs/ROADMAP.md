# Roadmap e Stato dello Sviluppo - C64 Coding Agent

Questo documento riassume lo stato attuale del progetto e definisce le prossime tappe per il miglioramento della robustezza e dell'usabilità.

## 📊 Stato Attuale

| Componente | Stato | Note |
| :--- | :--- | :--- |
| **Orchestrator** | ✅ Funzionante | Gestisce il flusso base e un round di self-healing. |
| **Researcher** | ✅ Funzionante | RAG con FAISS e Obsidian Wiki-links. |
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

### 3. Documentazione (Consolidamento)
- [x] **Unificazione Technical Manual**: Unificare i vari `DEEP_DIVE` in un unico manuale tecnico. (Implementato in `docs/TECHNICAL_MANUAL.md`)
- [x] **Aggiornamento README**: Inseriti link a Use Cases e Roadmap. (Completato)

---

## 🚀 Prossimi Passi (Evoluzione Futura)

- [ ] **Reranking semantico**: Migliorare la precisione del RAG con un cross-encoder.
- [x] **HyDE (Hypothetical Document Embeddings)**: Migliorare il recupero di documenti tecnici complessi. (Implementato)
- [x] **Cycle Counter per Assembly**: Analisi delle performance del codice generato. (Implementato in `utils/cycle_counter.py`)

---

## 📅 Cronologia Sviluppo

- **Fase 1: Rafforzamento Agenti**: Completata (Self-healing, BASIC validation, Memory tracking).
- **Fase 2: Refactoring UI e Feedback**: Completata (Config unificata, Logs in UI).
- **Fase 3: Simulazione Use Cases**: Completata (Documentati in `docs/USE_CASES.md`).
- **Fase 4: Aggiornamento Documentazione**: Completata.

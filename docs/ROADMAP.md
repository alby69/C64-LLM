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
- [ ] **Memory Protection**: Migliorare il `MemoryMapTracker` per segnalare sovrapposizioni tra codice e vettori di sistema.

### 2. Usabilità (Developer Experience)
- [ ] **Logging Centralizzato**: Migliore tracciabilità dei pensieri degli agenti nella UI.
- [ ] **Configurazione Unificata**: Spostare parametri (timeout, round, modelli) in un file YAML.
- [x] **Use Cases Documentati**: Aggiungere esempi reali di interazione nel README. (Implementato in `docs/USE_CASES.md`)

### 3. Documentazione (Consolidamento)
- [ ] Unificare i vari `DEEP_DIVE` in un unico manuale tecnico o organizzarli meglio.
- [ ] Aggiornare il `README.md` con una sezione dedicata agli "Use Cases".

---

## 📅 Scaletta delle Modifiche (Implementazione)

1. **Fase 1: Rafforzamento Agenti** (Validator & Orchestrator).
2. **Fase 2: Refactoring UI e Feedback**.
3. **Fase 3: Simulazione Use Cases e Test Finali**.
4. **Fase 4: Aggiornamento Documentazione Finale**.

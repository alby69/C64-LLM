# Evolution Plan: C64 Knowledge Engine (Updated)

Questo documento dettaglia la strategia per far evolvere il progetto C64-LLM verso un sistema più potente e ottimizzato.

## Stato Attuale (Fase 1 e 2 Completate)

- [x] **Migrazione Modello**: Supporto per Qwen2.5-Coder-1.5B via Transformers e GGUF.
- [x] **Backend Unificato**: Implementato `ModelBackend` e `LlamaCppBackend` per esecuzione su CPU/GPU.
- [x] **Prompt Management System (PMS)**: Centralizzato in `data/prompts/prompts.yaml`.
- [x] **Validazione Avanzata**: Migliorato `ValidatorAgent` con controlli specifici per BASIC v2.
- [x] **Memory Map Tracking**: L'Orchestratore ora traccia l'uso della memoria per prevenire collisioni.
- [x] **Refactoring KISS/DRY**: Logica della UI separata dal coordinamento degli agenti.

## Fase 3: Obsidian & Graph Integration (In Corso)

- [x] **ObsidianParser**: Implementato parsing di Wiki-links `[[...]]` e frontmatter YAML in `knowledge_base.py`.
- [x] **Graph Retrieval**: Il `ResearcherAgent` può esplorare link correlati per arricchire il contesto.
- [ ] **Visualizzazione Grafo**: Mostrare nella UI di Gradio le relazioni tra i documenti trovati.

## Fase 4: Ottimizzazione e Usabilità PC "Normali"

- [x] **Supporto GGUF**: Integrazione `llama-cpp-python` pronta all'uso.
- [ ] **Docker Optimization**: Riduzione dimensioni immagine per deployment rapido.
- [ ] **Installer Script**: Script unico per configurare ACME, VICE e ambiente Python.

## Prossimi Passi Suggeriti

1. **Espansione Knowledge Base**: Aggiungere più note tecniche su SID e VIC-II.
2. **Potenziamento Agenti**: Implementazione di Reranking, HyDE e Linter simbolici (Vedi [IMPLEMENTATION_PLAN_AGENTS.md](IMPLEMENTATION_PLAN_AGENTS.md)).
3. **Multi-step Reasoning**: Permettere all'Orchestratore di pianificare task complessi in più round.

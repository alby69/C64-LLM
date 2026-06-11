# Evolution Plan: C64 Knowledge Engine

Questo documento dettaglia la strategia per far evolvere il progetto C64-LLM verso un sistema più potente, ottimizzato per hardware limitato (16GB RAM, no GPU) e basato sulla conoscenza strutturata.

## 1. Migrazione del Modello: Qwen2.5-Coder-1.5B

Come suggerito dall'analisi, passeremo all'uso di **Qwen2.5-Coder-1.5B-Instruct**.

- **Perché**: È lo stato dell'arte per modelli sotto i 3B parametri nel coding. Supporta bene l'italiano e ha una comprensione del contesto tecnico superiore a Phi o versioni precedenti di Qwen.
- **Formato**: GGUF (via `llama.cpp` o `bitsandbytes` se usato in Python) per minimizzare l'occupazione di RAM a ~1-2 GB.

## 2. Da RAG a "Knowledge Engine" (Integrazione Obsidian)

Invece di un semplice database vettoriale "flat", implementeremo una struttura ispirata a Obsidian.

### Perché Obsidian/Markdown invece di LoRA?
- **Flessibilità**: Aggiungere un nuovo manuale (es. "GEOS Reference") è immediato come copiare un file .md.
- **Tracciabilità**: L'LLM può citare esattamente la nota o il file da cui ha tratto l'informazione.
- **Relazioni**: Sfruttando i link Wiki `[[NomeNota]]`, possiamo navigare la conoscenza per associazione logica, non solo per similarità vettoriale.

### Architettura Proposta
1.  **Vault Obsidian**: Una cartella `knowledge_base/` organizzata in sottocartelle (BASIC, SID, VIC-II, etc.).
2.  **Hybrid Retrieval**:
    - **Vettoriale**: Per trovare il punto di partenza (es. "come fare sprite multiplexing").
    - **Grafo**: Una volta trovato un documento (es. "Sprites"), il sistema carica anche i documenti collegati via Wiki-links (es. "Raster Interrupt", "VIC-II Registers") per completare il contesto.

## 3. Personalità Specializzate

Invece di un addestramento LoRA costoso e rigido, useremo **Dynamic System Prompts** (già parzialmente implementati):
- **C64 BASIC Expert**: Focus su brevità e compatibilità BASIC v2.
- **6510 Assembly Expert**: Focus su cicli macchina e sintassi ACME.

## 4. Roadmap di Implementazione

### Fase 1: Consolidamento (Attuale)
- [x] Deep Dive degli agenti.
- [x] Miglioramento Validatori (BASIC + ASM).
- [x] Personalità differenziate nel Coder.

### Fase 2: Obsidian Integration
- [ ] Implementazione di un `ObsidianParser` che estrae link `[[...]]`.
- [ ] Aggiornamento del `ResearcherAgent` per esplorare i link correlati durante la ricerca.
- [ ] Supporto per tag e metadati YAML nelle note.

### Fase 3: Ottimizzazione Locale
- [ ] Integrazione di `llama.cpp` come backend opzionale per massima velocità su CPU.
- [ ] UI Gradio migliorata per visualizzare il "percorso di ricerca" nel grafo di conoscenza.

## Conclusione

La strategia "Small Model + Huge Structured Context" è la via più efficiente per dominare un dominio tecnico ristretto e complesso come quello del Commodore 64 su hardware consumer.

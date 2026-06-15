# Piano di Miglioramento: Specializzazione e Disaccoppiamento Agenti

Per rendere il sistema più robusto e scalabile, proponiamo un'evoluzione verso un'architettura a "Capacità" (Capabilities) invece che a "Script".

## 1. Disaccoppiamento (Architecture)

### 1.1 Messaggistica Standardizzata
Gli agenti non si passeranno più stringhe arbitrarie, ma oggetti `AgentMessage` che contengono:
- `sender`: Chi ha generato il messaggio.
- `payload`: Il contenuto (codice, log, contesto).
- `metadata`: Token usati, tempo, flag di validazione.

### 1.2 Estrazione Utility (Utility-First)
Attualmente l'Orchestratore e il Validator gestiscono troppa logica C64. Sposteremo:
- **Memory Logic**: In un `MemoryAdvisor`.
- **Validation Logic**: In un `ValidationRegistry` che gestisce linter indipendenti.
- **Cycle Counting**: Già in `CycleCounter`.

## 2. Specializzazione (Agent Roles)

### 2.1 CoderAgent "Expert Profiles"
Il Coder diventerà un guscio che carica "Profili" (System Prompts + Few-shot) dinamicamente:
- `BASIC_V2_PROFILE`: Focus su memoria e numeri di riga.
- `ASM_6502_PROFILE`: Focus su cicli macchina e registri VIC/SID.
- `MATH_ROUTINES_PROFILE`: Focus su algoritmi a 8-bit.

### 2.2 ValidatorAgent "Plugin-based"
Invece di un unico grande metodo `validate`, useremo un sistema a plugin:
- `ACMEValidator`
- `BasicSyntaxLinter`
- `BasicVariableCollisionLinter`
- `AssemblyBranchLinter`
- `MemoryCollisionLinter`

### 2.3 ResearcherAgent "Context Orchestrator"
Il Researcher gestirà diversi canali di informazione:
- `VectorSearchChannel` (FAISS)
- `WikiGraphChannel` (Obsidian links)
- `SymbolTableChannel` (Registri C64 predefiniti)

## 3. Implementazione (Step-by-Step)

1.  **Creazione `MemoryAdvisor`**: Disaccoppiare la gestione della memoria dall'Orchestratore.
2.  **Refactoring `ValidatorAgent`**: Implementare il sistema a plugin.
3.  **Refactoring `CoderAgent`**: Implementare il sistema a profili dinamici.
4.  **Integrazione `AgentMessage`**: Standardizzare la comunicazione.

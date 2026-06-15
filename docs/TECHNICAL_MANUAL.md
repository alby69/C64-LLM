# Manuale Tecnico: C64 Coding Agent

Benvenuti nel manuale tecnico del C64 Coding Agent. Questo documento consolida le specifiche, l'architettura e le strategie di tutti gli agenti del sistema.

## 🤖 Architettura Multi-Agente

Il sistema è composto da 5 agenti specializzati che collaborano per risolvere compiti di programmazione per Commodore 64.

### 1. OrchestratorAgent (Il Direttore)
L'Orchestratore coordina il flusso di lavoro.
- **Flusso**: Riceve la query -> Attiva il Researcher -> Passa il contesto al Coder -> Valida l'output con il Validator -> Gestisce il Self-Healing se necessario.
- **Memoria**: Gestisce il `MemoryMapTracker` per evitare collisioni tra turni di chat.
- **Trasparenza**: Genera log dettagliati dei "pensieri" del sistema visibili nella UI.

### 2. ResearcherAgent (L'Esperto di Dominio)
Il Researcher è responsabile del recupero di informazioni tecniche.
- **RAG Avanzato**: Utilizza FAISS per la ricerca vettoriale e supporta i Wiki-links di Obsidian per esplorare il grafo della conoscenza.
- **HyDE**: Genera una risposta ipotetica per migliorare la qualità del recupero.
- **Multi-turn**: Analizza la cronologia della chat per risolvere anafore e mantenere il contesto.

### 3. CoderAgent (Il Programmatore)
Il Coder genera il codice effettivo (BASIC o Assembly).
- **Chain-of-Thought (CoT)**: Ogni risposta inizia con una fase di analisi e pianificazione.
- **Personalità**: Adatta lo stile (BASIC V2 o 6510 Assembly) in base al linguaggio rilevato.
- **PMS**: Carica i prompt dinamicamente tramite il Prompt Management System.

### 4. ValidatorAgent (Il Revisore)
Il Validator garantisce la correttezza formale e tecnica.
- **Assembly**: Utilizza l'assembler ACME per la validazione sintattica. Verifica anche branch fuori range e terminazione corretta (RTS/JMP).
- **BASIC**: Parser dedicato che controlla:
    - Numeri di riga sequenziali.
    - Limiti POKE/PEEK.
    - Collisioni di variabili (C64 BASIC usa solo i primi 2 caratteri).
    - Lunghezza delle linee.

### 5. WebCrawlerAgent (Il Ricercatore Proattivo)
Un agente offline che popola il Knowledge Base.
- **Fonti**: Monitora Wiki, GitHub e archivi PDF (Zimmers, Archive.org).
- **Trasformazione**: Converte documentazione complessa e PDF in note Markdown strutturate per Obsidian.

## 🛠️ Componenti Tecnici

### MemoryMapTracker
Sistema per tracciare le allocazioni di memoria nel C64:
- Estrae indirizzi da `* = $XXXX` in Assembly.
- Rileva sovrapposizioni tra codice utente e vettori di sistema ($0314, $FFFA, ecc.).

### Prompt Management System (PMS)
- Centralizza i prompt in `prompts/prompts.yaml`.
- Supporta il rendering dinamico tramite Jinja2.

### Configurazione Unificata
- Gestita in `config/agent_config.yaml`.
- Permette di modificare parametri come temperatura, numero di tentativi di self-healing e librerie prompt della UI senza toccare il codice.

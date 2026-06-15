# Manuale Tecnico Completo: C64 Coding Agent

Questo documento rappresenta la risorsa definitiva per l'architettura, il funzionamento e l'evoluzione del C64 Coding Agent.

## 1. Visione d'Insieme

Il C64 Coding Agent è un sistema multi-agente progettato per assistere nello sviluppo di software per Commodore 64 (Assembly 6502 e BASIC v2). Combina una pipeline di dati proattiva (Crawler + RAG) con un'architettura di ragionamento strutturata (Chain-of-Thought) e un ciclo di validazione con self-healing.

---

## 2. Architettura degli Agenti

Il sistema opera tramite la collaborazione di 5 agenti core, coordinati da un Orchestratore centrale.

### 2.1 OrchestratorAgent (Coordinamento e Self-Healing)
È il cervello del sistema. Gestisce il ciclo di vita di una richiesta:
1.  **Analisi & Ricerca**: Attiva il `Researcher` per ottenere il contesto tecnico.
2.  **Generazione**: Passa query e contesto al `Coder`.
3.  **Validazione**: Invia il codice generato al `Validator`.
4.  **Self-Healing**: Se la validazione fallisce, attiva un ciclo di correzione automatica (fino a 3 tentativi) fornendo i log d'errore al Coder.

### 2.2 ResearcherAgent (RAG + HyDE)
Specializzato nel recupero di informazioni dalla "Knowledge Engine":
- **Query Expansion**: Trasforma richieste vaghe in termini tecnici C64.
- **HyDE (Hypothetical Document Embeddings)**: Genera una risposta ipotetica per migliorare il matching vettoriale nel database FAISS.
- **Graph Navigation**: Supporta Wiki-links in stile Obsidian per navigare tra documenti correlati (es. da "VIC-II" a "Sprite Registers").

### 2.3 CoderAgent (Sintesi di Codice)
L'agente esecutivo che scrive il codice:
- **Expert Profiles**: Assume personalità diverse (BASIC Expert o Assembly Expert) in base al task.
- **Chain-of-Thought (CoT)**: Ogni risposta include una sezione di pianificazione logica prima dell'implementazione.
- **Addressing Mode Awareness**: Ottimizzato per scegliere le modalità di indirizzamento corrette (Zero Page vs Absolute).

### 2.4 ValidatorAgent (Analisi Statica e Compilazione)
Garantisce la qualità del codice:
- **Assembly**: Integra l'assembler ACME. Esegue check preventivi su branch fuori range (+/- 127 byte) e terminazione delle routine (RTS/JMP).
- **BASIC v2**: Parser interno per:
    - Numeri di riga sequenziali.
    - Collisioni di variabili (considera solo i primi 2 caratteri, es. `SCORE1` vs `SCORE2`).
    - Range di POKE/PEEK e bilanciamento FOR/NEXT.
- **Cycle Counter**: Fornisce una stima dei cicli di clock per le routine Assembly.

### 2.5 WebCrawlerAgent (Acquisizione Conoscenza)
Agente proattivo che monitora fonti autorevoli (C64-Wiki, GitHub, Zimmers, Archive.org) per mantenere aggiornato il Knowledge Base locale.

---

## 3. Knowledge Engine (RAG)

Il sistema RAG (Retrieval-Augmented Generation) è il cuore della precisione tecnica dell'agente.
- **Vault Obsidian**: La documentazione è strutturata in Markdown con frontmatter YAML per tag e categorie.
- **Indicizzazione**: Utilizza `sentence-transformers/all-MiniLM-L6-v2` per creare embedding vettoriali memorizzati in FAISS.
- **Pipeline**: Include strumenti di pulizia per normalizzare il testo estratto da PDF tecnici e magazine storici (The Transactor, Compute!, ecc.).

---

## 4. Guide all'Utilizzo e Casi d'Uso

### 4.1 Generazione Raster Interrupt (Assembly)
L'utente chiede un effetto grafico. L'agente recupera i registri VIC-II ($D012), imposta il vettore IRQ ($0314) e valida il codice con ACME.

### 4.2 Classifica in BASIC
L'agente gestisce array (`DIM`) e input, validando che i nomi delle variabili non collidano e che i numeri di riga siano ordinati.

---

## 5. Configurazione e Personalizzazione

Il sistema è altamente configurabile tramite `config/agent_config.yaml`:
- **agent.max_attempts**: Numero di round di self-healing.
- **rag.use_hyde**: Abilita/disabilita la generazione ipotetica.
- **ui.prompt_library**: Lista di prompt predefiniti nella Gradio UI.

---

## 6. Evoluzione e Roadmap

Il progetto mira a diventare un ambiente di sviluppo retrocomputing completo con:
- **Multi-step Reasoning**: Scomposizione di task complessi (es. "scrivi un intero gioco") in sotto-task gestiti sequenzialmente.
- **Symbolic Linter**: Analisi approfondita dei simboli Assembly e delle aree di memoria riservate dal KERNAL.
- **Integrazione IDE**: Possibilità di esportare direttamente file `.prg` pronti per l'emulatore.

# Piano di Miglioramento: C64 Coding Agent

Dopo un'analisi approfondita del codice e della documentazione, ecco il piano di miglioramento strutturato per rendere il progetto più manutenibile, efficiente (anche su PC consumer) ed estendibile.

## 1. Architettura e Pulizia (KISS & DRY)

*   **Consolidamento UI (`agent/agent_pro.py`)**: Attualmente la UI contiene logica duplicata e inizializzazione manuale degli agenti. Sposteremo tutta la logica di coordinamento nell'`OrchestratorAgent` e useremo la UI solo come interfaccia.
*   **Backend Unificato**: Migliorare `ModelBackend` per gestire in modo trasparente sia i modelli carichi via `transformers` (con quantizzazione 4-bit) sia quelli via `llama.cpp` (GGUF) per chi non ha GPU.
*   **Gestione Errori Robusta**: Migliorare il `PromptManager` per gestire la mancanza dei file di configurazione senza crashare, fornendo default sensati.

## 2. Potenziamento del Knowledge Engine (RAG+)

*   **Obsidian Integration**: Implementare pienamente il parsing dei Wiki-links `[[Nota]]` per permettere al `ResearcherAgent` di esplorare i documenti correlati.
*   **Graph Retrieval**: Sfruttare le relazioni tra i documenti per fornire al Coder un contesto più ricco e strutturato (es. se cerchi "Sprite", carica anche "VIC-II Registers").

## 3. Intelligenza e Validazione

*   **Memory Map Tracker**: Introdurre un sistema di tracciamento della memoria C64 nell'Orchestratore per evitare conflitti (es. non usare la stessa area di memoria per codice e dati se non richiesto).
*   **Validatore BASIC Avanzato**: Migliorare `ValidatorAgent` per rilevare errori comuni del BASIC v2 (es. variabili troppo lunghe, oltre i 2 caratteri significativi).
*   **Self-Healing Migliorato**: Permettere più round di correzione automatica se l'errore persiste.

## 4. Usabilità su Hardware "Normali"

*   **Ottimizzazione GGUF**: Finalizzare l'integrazione di `LlamaCppBackend`. Un modello da 1.5B in formato Q4_K_M occupa meno di 1GB di RAM e gira velocemente su qualsiasi CPU moderna.
*   **Docker Ready**: Ottimizzare il `Dockerfile` per build multi-stage, riducendo la dimensione dell'immagine finale.

---

*Questo piano mira a trasformare un prototipo funzionale in uno strumento di sviluppo solido e accessibile per tutti gli appassionati di retrocomputing.*

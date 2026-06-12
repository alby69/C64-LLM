# Piano di Implementazione Approfondito: Evoluzioni Agenti

Questo documento dettaglia la strategia di implementazione per le evoluzioni future degli agenti (Researcher, Coder, Validator, Orchestrator) come delineato nei documenti DEEP_DIVE.

## 1. ResearcherAgent: Precisione e Context-Awareness

L'obiettivo è trasformare il Researcher in un motore di ricerca semantica di livello professionale.

### 1.1 Reranking (Cross-Encoding)
- **Azione**: Integrare `SentenceTransformerRerank` o un modulo simile.
- **Dettaglio**:
    1. La ricerca vettoriale iniziale recupera i primi 10-15 frammenti.
    2. Un modello Cross-Encoder (es. `cross-encoder/ms-marco-MiniLM-L-6-v2`) valuta la coppia (Query, Frammento).
    3. Vengono passati al Coder solo i primi 3-5 frammenti con il punteggio più alto.
- **Vantaggio**: Riduce drasticamente il "rumore" nel contesto fornito al Coder.

### 1.2 HyDE (Hypothetical Document Embeddings)
- **Azione**: Aggiungere un passaggio di "generazione ipotetica" nel metodo `research`.
- **Dettaglio**:
    1. Prima della ricerca, l'LLM genera un paragrafo tecnico che descrive la soluzione ideale (senza preoccuparsi della precisione assoluta).
    2. Si usa il vettore di questa generazione per interrogare FAISS.
- **Vantaggio**: Migliora il matching con documenti che usano terminologia tecnica specifica che l'utente potrebbe non conoscere.

### 1.3 Multi-turn Memory (Implementato)
- **Azione**: Iniettare la `chat_history` nel processo di `expand_query`.
- **Dettaglio**: Il prompt di espansione riceve gli ultimi 2 scambi per risolvere anafore.

---

## 2. CoderAgent: Ottimizzazione e Qualità del Codice

Il Coder deve passare da "generatore di codice" a "esperto di ottimizzazione".

### 2.1 Dynamic Few-Shot (Knowledge Injection)
- **Azione**: Creare una libreria di "Snippet Perfetti" nel Knowledge Base.
- **Dettaglio**: Se il Researcher identifica un task comune (es. "raster interrupt"), l'Orchestratore inietta un esempio di codice validato e ottimizzato nel prompt del Coder come riferimento `few-shot`.

### 2.2 Symbolic Linter per Assembly
- **Azione**: Implementare un modulo `AssemblyLinter` in `utils/`.
- **Dettaglio**:
    - Verifica che tutte le etichette (`labels`) siano definite.
    - Controlla che le istruzioni non sovrascrivano aree di memoria riservate (es. vettori KERNAL) a meno che non sia intenzionale.
    - Avvisa se il codice supera la dimensione prevista del segmento.

### 2.3 Cycle Counter (Ottimizzatore)
- **Azione**: Sviluppare un tool che calcoli i cicli di clock delle routine generate.
- **Dettaglio**: Fornire al Coder un feedback: "Questa routine impiega 45 cicli, puoi scendere a 38 usando lo zero-page indexing?".

---

## 3. ValidatorAgent: Rigore e Correttezza

Il Validator deve diventare un vero e proprio compilatore/analizzatore statico.

### 3.1 Parser BASIC v2 Avanzato (In Corso)
- **Azione**: Espandere `validate_basic` in `agent/validator.py`.
- **Dettaglio**:
    - **Controllo Limiti (Implementato)**: Verifica che i valori `POKE` siano tra 0-255 e gli indirizzi tra 0-65535.
    - **Stack Overflow**: Analisi rudimentale di `GOSUB` annidati senza `RETURN`.
    - **Keyword Check**: Assicurarsi che non vengano usati comandi di versioni successive del BASIC.

### 3.2 Analisi Statica Assembly (Branch Check) (Implementato)
- **Azione**: Analizzare i salti relativi (`BNE`, `BEQ`, ecc.).
- **Dettaglio**: Calcolato preventivamente lo scostamento tra branch e label per evitare errori fuori range (+/- 127 byte).

### 3.3 Logical Flow Validation (Implementato)
- **Azione**: Verifica della terminazione delle routine.
- **Dettaglio**: Verifica che i blocchi assembly finiscano con `RTS`, `RTI`, `JMP` o `BRK`.

---

## 4. OrchestratorAgent: Ragionamento Complesso

L'Orchestratore deve gestire task di alto livello scomponendoli.

### 4.1 Multi-step Reasoning (Task Decomposition)
- **Azione**: Implementare un ciclo di pianificazione ricorsivo.
- **Dettaglio**:
    - L'utente chiede: "Scrivi una demo con musica e sprite".
    - L'Orchestratore scompone in: 1. Setup VIC-II, 2. Caricamento Sprite, 3. Setup IRQ musica.
    - Gestisce ogni task sequenzialmente, mantenendo lo stato globale.

### 4.2 Proactive Memory Mapping (Implementato)
- **Azione**: L'Orchestratore suggerisce attivamente indirizzi liberi.
- **Dettaglio**: L'Orchestratore suggerisce ora aree come $C000 o $1000 se non ancora allocate dal tracker.

### 4.3 Integrazione Obsidian-Wiki Estesa
- **Azione**: Navigazione automatica del grafo basata sulla confidenza.
- **Dettaglio**: Se i risultati iniziali hanno un basso punteggio di similarità, l'Orchestratore ordina al Researcher di esplorare i nodi linkati a quelli trovati per trovare informazioni più pertinenti.

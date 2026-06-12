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

### 1.3 Multi-turn Memory
- **Azione**: Iniettare la `chat_history` nel processo di `expand_query`.
- **Dettaglio**: Il prompt di espansione riceverà gli ultimi 2-3 scambi per risolvere anafore (es. "e ora fallo blu" -> "cambia il colore del bordo a blu").

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

### 3.1 Parser BASIC v2 Avanzato
- **Azione**: Espandere `validate_basic` in `agent/validator.py`.
- **Dettaglio**:
    - **Controllo Limiti**: Verifica che i valori `POKE` siano tra 0-255 e gli indirizzi tra 0-65535.
    - **Stack Overflow**: Analisi rudimentale di `GOSUB` annidati senza `RETURN`.
    - **Keyword Check**: Assicurarsi che non vengano usati comandi di versioni successive del BASIC.

### 3.2 Analisi Statica Assembly (Branch Check)
- **Azione**: Analizzare i salti relativi (`BNE`, `BEQ`, ecc.).
- **Dettaglio**: Calcolare la distanza tra il branch e la label. Se supera +/- 127 byte, segnalare errore prima ancora di chiamare ACME (risparmio di risorse).

### 3.3 Logical Flow Validation
- **Azione**: Verifica della terminazione delle routine.
- **Dettaglio**: Assicurarsi che i blocchi di codice finiscano con `RTS`, `RTI` o un loop infinito (`JMP *`), per evitare che la CPU "scivoli" in aree di memoria casuali.

---

## 4. OrchestratorAgent: Ragionamento Complesso

L'Orchestratore deve gestire task di alto livello scomponendoli.

### 4.1 Multi-step Reasoning (Task Decomposition)
- **Azione**: Implementare un ciclo di pianificazione ricorsivo.
- **Dettaglio**:
    - L'utente chiede: "Scrivi una demo con musica e sprite".
    - L'Orchestratore scompone in: 1. Setup VIC-II, 2. Caricamento Sprite, 3. Setup IRQ musica.
    - Gestisce ogni task sequenzialmente, mantenendo lo stato globale.

### 4.2 Proactive Memory Mapping
- **Azione**: L'Orchestratore suggerisce attivamente indirizzi liberi.
- **Dettaglio**: Invece di limitarsi a tracciare la memoria, l'Orchestratore dice al Coder: "Usa l'area $C000-$CFFF perché è libera e sicura".

### 4.3 Integrazione Obsidian-Wiki Estesa
- **Azione**: Navigazione automatica del grafo basata sulla confidenza.
- **Dettaglio**: Se i risultati iniziali hanno un basso punteggio di similarità, l'Orchestratore ordina al Researcher di esplorare i nodi linkati a quelli trovati per trovare informazioni più pertinenti.

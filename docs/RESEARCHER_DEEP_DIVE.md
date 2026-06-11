# Deep Dive: ResearcherAgent

Il `ResearcherAgent` è il componente critico che garantisce che il `CoderAgent` non lavori "nel vuoto", ma sia supportato da documentazione tecnica accurata.

## Come Lavora (Flusso Attuale)

1.  **Analisi & Espansione (Query Expansion)**:
    - L'input dell'utente (es: "come cambio il colore del bordo?") è spesso troppo generico per una ricerca vettoriale efficace su manuali tecnici.
    - Il Researcher usa l'LLM con un prompt a "bassa temperatura" (0.1) per tradurre la richiesta in termini tecnici C64.
    - *Esempio*: "cambio colore bordo" -> "$D020, VIC-II, border color, register".

2.  **Ricerca Vettoriale (FAISS)**:
    - Utilizza gli embedding di `sentence-transformers` per cercare nei documenti indicizzati (Markdown e output della pipeline).
    - Recupera i Top-K frammenti più simili alla query espansa.

3.  **Sintesi del Context Brief**:
    - Combina i frammenti trovati, includendo i metadati (come il file sorgente), in un blocco di testo strutturato che viene iniettato nel prompt del Coder.

## Punti di Forza dell'Implementazione "Opzione A"
- **Zero Overhead di Memoria**: Condividendo l'istanza del modello con il Coder, il Researcher non occupa RAM aggiuntiva.
- **Precisione Tecnica**: L'espansione della query riduce drasticamente il rischio di non trovare informazioni presenti ma scritte con un linguaggio diverso da quello dell'utente.

## Come Possiamo Migliorarlo (Evoluzioni Future)

1.  **Reranking (Cross-Encoding)**:
    - Dopo aver recuperato i primi 10-20 frammenti con la ricerca vettoriale (veloce ma meno precisa), potremmo usare un modello di reranking più piccolo per selezionare i 3 migliori. Questo migliora la "Signal-to-Noise Ratio".

2.  **Rilevamento del Linguaggio (ASM vs BASIC)**:
    - Il Researcher potrebbe pre-classificare la richiesta. Se l'utente chiede BASIC, il Researcher può filtrare i documenti escludendo quelli puramente Assembly, evitando di confondere il Coder.

3.  **HyDE (Hypothetical Document Embeddings)**:
    - Invece di espandere solo le parole chiave, il Researcher potrebbe generare una "risposta ipotetica" e usare quella per la ricerca. Spesso la risposta ipotetica è più vicina vettorialmente al documento reale rispetto alla domanda.

4.  **Multi-turn Memory**:
    - Integrare la cronologia della conversazione nella fase di ricerca per mantenere il contesto di ciò di cui si è parlato precedentemente (es: "e ora cambia anche il colore dello sfondo").

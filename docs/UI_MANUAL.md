# Manuale dell'Interfaccia Utente (UI)

Il C64 Coding Assistant espone un'interfaccia web Gradio su `http://localhost:7860` con 4 tab principali.

---

## Tab 1: Chat

Interfaccia conversazionale principale con l'agente C64.

### Componenti

| Elemento | Descrizione |
|----------|-------------|
| **Chatbot** | Area conversazione: messaggi utente (destra) e risposte agente (sinistra) |
| **Textbox** | Input per scrivere il messaggio all'agente |
| **Usa Knowledge Base (RAG)** | Checkbox: se attivo, la risposta viene arricchita con il contesto dell'indice FAISS |
| **Auto-elabora link** | Checkbox: se attivo, estrae automaticamente gli URL dal messaggio e dalla risposta, li aggiunge ai siti personalizzati e avvia la pipeline di download/elaborazione/KB rebuild. Utile per incollare liste di link da sorgenti esterne (es. Claude, ChatGPT). |
| **Tentativi Self-Healing** | Slider 1-5: numero di tentativi di auto-correzione in caso di codice non valido |
| **Prompt Library** | Dropdown di snippet predefiniti: clicca un prompt per inserirlo nella textbox |
| **Technical Terms** | Nuvola di tag interattiva con ~160 termini tecnici C64 (registri VIC-II, SID, CIA, istruzioni 6502, comandi BASIC, concetti). Clicca un termine per inserirlo nella chat. Filtra in tempo reale con la casella "Cerca". |

### Comportamento "Auto-elabora link"

Quando la checkbox è attiva:

1. Invia un messaggio contenente URL (o l'agente risponde con URL)
2. Il sistema estrae TUTTI gli URL dal tuo messaggio e dalla risposta
3. Ogni URL viene aggiunto a `data/custom_sites.json` (saltando duplicati)
4. Per ogni URL, viene eseguita la pipeline completa:
   - `scrape_docs.py` (cerca PDF nel sito)
   - `scrape_url.py` (cerca codice Assembly)
   - Estrazione testo da PDF
   - Pulizia testo (`text_cleaner.py`)
   - Generazione dataset (`build_dataset.py`)
   - Rebuild Knowledge Base
5. Il progresso viene mostrato in tempo reale nella chat

---

## Tab 2: Scarica e Siti

Due sezioni affiancate per download singolo e scraping batch.

### Scarica URL (colonna sinistra)

Inserisci un URL e clicca **Scarica e Integra**. Supporta:

| Tipo URL | Esempio | Cosa fa |
|----------|---------|---------|
| **Google Drive** | `https://drive.google.com/drive/folders/...` | Enumera tutti i file nella cartella (con skip_download), mostra riepilogo per sottocartella, poi scarica file per file con fallback su richieste dirette in caso di rate limiting. Ritardo di 1.5s tra file. |
| **Archive.org** | `https://archive.org/details/...` | Analizza metadati, seleziona miglior formato (TXT > EPUB > HTML > PDF), scarica + estrae D64/G64/PRG se presenti |
| **PDF diretto** | `.../documento.pdf` | Download diretto + pipeline |
| **D64/G64/PRG** | `.../gioco.d64` | Download + estrazione contenuti |
| **Sito web** | `https://codebase64.org/...` | Esegue scrape_docs.py (cerca PDF) + scrape_url.py (cerca codice ASM) |

#### Controlli processo

- **Avvia**: start download/elaborazione
- **Pausa**: sospende il processo (SIGSTOP)
- **Riprendi**: riprende il processo (SIGCONT)
- **Annulla**: termina il processo

### Gestione siti (colonna destra)

- **Aggiungi sito**: inserisci nome e URL, clicca "Aggiungi". Il sito viene salvato in `data/custom_sites.json` e appare nella checkbox group.
- **Rimuovi sito**: seleziona un sito dal dropdown e clicca "Rimuovi".
- **Checkbox group**: seleziona uno o più siti (predefiniti + personalizzati) e clicca **Scrapa Selezionati** per avviare lo scraping batch.

### Siti Predefiniti

- 6502.org
- Codebase64
- C64-Wiki
- The Fridge
- Lemon64
- Project 64
- NESdev 6502

---

## Tab 3: Knowledge Base

Gestione dell'indice vettoriale FAISS e navigazione dei file sorgente.

### Ricostruisci Indice KB

Pulsante **Ricostruisci Indice KB** — ricostruisce l'indice FAISS da zero leggendo:

- `knowledge_base/*.md` — tutorial e documentazione con frontmatter
- `data/output/clean.txt` — testo pulito dalla pipeline
- `data/input/*.bas.txt` — BASIC detokenizzato
- `data/input/*.ml.txt` — codice macchina estratto
- `data/src/*.asm` — Assembly scrapato dal web

Lo splitter usa `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)` con separatori `["\\n\\n", "\\n", ".", " ", ""]`.

I file binari (`.gz`, `.zip`, `.png`, `.pdf`, `.d64`, ecc.) vengono saltati automaticamente tramite `SKIP_EXTS`.

### Esplora file KB

- **Elenca tutti i file**: mostra ricorsivamente tutti i file in `knowledge_base/`, `data/input/`, `data/src/` con dimensione
- **Cerca file**: filtro case-insensitive per nome file o percorso
- **Anteprima file**: dropdown per selezionare un file, clicca "Visualizza" per mostrare le prime 50 righe

---

## Tab 4: Dati

### Dataset Viewer

Visualizza il contenuto di `data/output/dataset_unified.jsonl` con:

- **Paginazione**: pulsanti ◀ Precedente / Successiva ▶ (20 righe per pagina)
- **Ricerca**: casella di testo + pulsante "Cerca" — filtra le righe per parola chiave (case-insensitive)
- **Visualizzazione a card orizzontali**: ogni entry del dataset è una card con:
  - Numero progressivo
  - Istruzione (campo `instruction`)
  - Contesto (campo `context`)
  - Vincoli (campo `constraints`, mostrati come tag)
  - Output (campo `output`, in un blocco codice scrollabile)
  - Scroll orizzontale con barra in basso per navigare tra le card

### Statistiche

Pulsante **Aggiorna** — mostra statistiche sul dataset corrente:
- Numero di entry nel dataset
- Dimensione dei file nella KB
- Stato dell'indice vettoriale

---

## Process Control (Globale)

Il sistema ha un controllo processo globale (`ProcessControl`) che gestisce:
- **Pausa**: sospende il subprocess attivo via SIGSTOP
- **Riprendi**: riprende il subprocess via SIGCONT
- **Annulla**: termina il gruppo processo via killpg()

I pulsanti Pausa/Riprendi/Annulla sono disponibili nel tab "Scarica e Siti".

---

## Scorciatoie e Consigli

1. **Per aggiungere documenti alla KB**: incolla URL di Archive.org, Google Drive, o siti web nel tab "Scarica e Siti"
2. **Per arricchire la KB velocemente**: usa la chat con "Auto-elabora link" attivo e incolla una lista di URL
3. **Per verificare il contenuto del dataset**: vai al tab "Dati" e usa la ricerca con paginazione
4. **Per cercare un file specifico nella KB**: tab "Knowledge Base" → "Cerca file"
5. **Technical Terms**: clicca un termine nella nuvola per inserirlo direttamente nella chat

# Manuale dell'Interfaccia Utente (UI)

Il C64 Coding Assistant espone un'interfaccia web Gradio su `http://localhost:7860` con 5 tab principali.

---

## Tab 1: Chat

Interfaccia conversazionale principale con l'agente C64.

### Componenti

| Elemento | Descrizione |
|----------|-------------|
| **Chatbot** | Area conversazione: messaggi utente (destra) e risposte agente (sinistra) |
| **Textbox** | Input per scrivere il messaggio all'agente |
| **Modalità** | Radio con 4 opzioni: **Base** (solo modello, nessun potenziamento), **RAG** (Knowledge Base FAISS, default), **LoRA** (modello affinato, nessuna KB), **RAG+LoRA** (entrambi: KB per contesto + LoRA per stile) |
| **Auto-elabora link** | Checkbox: se attivo, estrae automaticamente gli URL dal messaggio e dalla risposta, li aggiunge ai siti personalizzati e avvia la pipeline di download/elaborazione/KB rebuild. Utile per incollare liste di link da sorgenti esterne (es. Claude, ChatGPT). |
| **Tentativi Self-Healing** | Slider 1-5: numero di tentativi di auto-correzione in caso di codice non valido |
| **LoRA** | Sezione nella barra laterale: dropdown **Checkpoint** per selezionare un modello LoRA addestrato, pulsante **Applica LoRA** per caricarlo/subirlo, pulsante **🔄** per aggiornare la lista, textbox **Stato** che mostra il checkpoint attivo. |
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
   - Estrazione testo da PDF via pdf2marker (usa marker-pdf se disponibile, altrimenti PyMuPDF)
   - Pulizia testo su .txt (`text_cleaner.py`)
   - Inclusione .md marker (boost 1.2, solo se marker-pdf installato) e _clean.txt (boost 0.3) nella KB
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

- `data/kb/manuali/*.md` — tutorial e documentazione con frontmatter
- `data/raw/*.bas.txt` — BASIC detokenizzato
- `data/raw/*.ml.txt` — codice macchina estratto
- `data/raw/*.asm` — Assembly scrapato dal web

**Nota**: I file `data/kb/*.txt` (estrazioni OCR da PDF) NON vengono più indicizzati dalla KB — causavano allucinazioni tecniche nel modello.

Lo splitter usa `RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)` con separatori `["\\n\\n", "\\n", ".", " ", ""]`.

I file binari (`.gz`, `.zip`, `.png`, `.pdf`, `.d64`, ecc.) vengono saltati automaticamente tramite `SKIP_EXTS`.

### Documenti KB (Manuali)

| File | Argomento |
|------|-----------|
| `c64_memory_map.md` | Mappa memoria C64 (ROM, RAM, I/O) |
| `c64_basic_tutorial.md` | Tutorial BASIC v2 per programmatori ASM |
| `c64_screen_routines.md` | Routine schermo: clear, scroll, charset |
| `vic2_registers.md` | Registri VIC-II ($D000-$D03F) completi |
| `raster_interrupts.md` | Raster interrupt: setup, split, multi-line |
| `sprite_programming.md` | Sprite: pointer, posizione, multicolor, collisioni |
| `sid_programming.md` | SID: voci, ADSR, forme d'onda, filtro, frequenze |
| `kernal_routines.md` | KERNAL: screen I/O, LOAD/SAVE, vettori |
| `6502_addressing_modes.md` | 13 modalità di indirizzamento 6502 con esempi C64 |

### Esplora file KB

- **Elenca tutti i file**: mostra ricorsivamente tutti i file in `data/kb/manuali/`, `data/raw/`, `data/raw/` con dimensione
- **Cerca file**: filtro case-insensitive per nome file o percorso
- **Anteprima file**: dropdown per selezionare un file, clicca "Visualizza" per mostrare le prime 50 righe. I file binari (PDF, D64, PNG, ecc.) mostrano un messaggio "File binario" invece di crashare.

---

## Tab 4: Distillazione

Interfaccia per la Knowledge Distillation: generazione di dataset sintetici da Knowledge Base + training LoRA dello studente Qwen2.5-Coder-1.5B-Instruct.

### Guida rapida

1. **Scegli un profilo** dal dropdown "Profilo" (es. ⚡ Rapido, 🔧 Groq Veloce, 🤖 Ollama Locale) — i parametri si impostano automaticamente. Puoi modificarli manualmente e salvare il risultato come nuovo profilo con **💾 Salva**.
2. **Configura il Teacher**: se usi `opencode` (default) nessuna API key necessaria. Per Groq/OpenRouter/HF seleziona backend, modello e inserisci la chiave.
3. **Genera Dataset**: clicca **🚀 Genera Dataset** — il log mostra i chunk processati in tempo reale. Il dataset viene salvato in `data/kb/distill_dataset.jsonl`.
4. **Addestra (LoRA)**: clicca **🏋️ Addestra (LoRA)** per avviare il training su Qwen2.5-Coder-1.5B col dataset generato. Usa **📊 Stato** per verificare entry e configurazione attiva.

### Profili di Configurazione

Il sistema a profili permette di salvare e ripristinare configurazioni complete con un click.

| Elemento | Descrizione |
|----------|-------------|
| **Profilo** | Dropdown con tutti i profili disponibili (predefiniti + personalizzati). La selezione imposta automaticamente tutti i parametri sottostanti. |
| **Salva come...** | Textbox per inserire il nome del nuovo profilo. |
| **💾 Salva** | Salva la configurazione corrente come nuovo profilo personalizzato in `config/distill_profiles.json`. |
| **🗑️ Elimina** | Elimina il profilo attualmente selezionato (solo profili personalizzati, non i predefiniti). |

#### Profili Predefiniti

| Profilo | Backend | Tipi | Lingue | QA/chunk | Max chunks |
|---------|---------|------|--------|----------|------------|
| **⚡ Rapido (base)** | opencode | factual, code, explain | it, en | 2 | 50 |
| **🇮🇹 Solo Italiano** | opencode | code, theory | it | 3 | 100 |
| **🌍 Completo (tutti i tipi)** | opencode | factual, code, explain, bugfix, theory | it, en | 2 | 200 |
| **🏋️ Qualità Expert** | opencode | factual, theory | it, en | 1 | 30 |
| **🔧 Groq Veloce** | groq (mixtral) | factual, code, bugfix | en | 3 | 100 |
| **🤖 Ollama Locale** | ollama (llama3) | factual, code, explain, theory | it, en | 2 | 50 |

### Configurazione Teacher

| Elemento | Descrizione |
|----------|-------------|
| **Backend** | Dropdown per selezionare il Teacher LLM: `opencode` (default, nessuna API key), `groq`, `openrouter`, `ollama`, `huggingface` |
| **Modello** | Textbox per specificare il modello Teacher (es. `mixtral-8x7b-32768` per Groq, `gpt-4o` per OpenRouter) |
| **API Key** | Textbox (password field) per la chiave API del backend scelto (non necessaria per `opencode` e `ollama`; mai salvata nei profili per sicurezza) |

### Strategia di generazione

| Elemento | Descrizione |
|----------|-------------|
| **Tipi di dato** | Checkbox group per selezionare i tipi di dato da generare: `factual` (Q&A fattuale), `code` (generazione codice), `explain` (spiegazione codice), `bugfix` (correzione bug), `theory` (teoria e concetti) |
| **Lingue** | Checkbox group per selezionare le lingue: `it` (italiano), `en` (english) |
| **QA per chunk** | Slider 1-5: numero di QA pairs da generare per ogni chunk di contesto |
| **Max chunks** | Slider 10-500: numero massimo di chunk da processare dalla Knowledge Base |
| **Filtri qualità** | Accordion espandibile con: lunghezza minima risposta (10-200), test Assembly con ACME, test BASIC sintattico |
| **🚀 Genera Dataset** | Pulsante per avviare la corrispondente azione. Mostra log in tempo reale nella textbox "Log" sottostante. |
| **📄 Placeholder** | Genera 1 singolo esempio fittizio per testare il training senza dover generare l'intero dataset. |

### Training LoRA

| Elemento | Descrizione |
|----------|-------------|
| **Dataset path** | Textbox con il path del dataset JSONL generato (default: `data/kb/distill_dataset.jsonl`) |
| **Output dir** | Textbox con la directory di output per i checkpoint LoRA (default: `data/models/c64-lora-pro`) |
| **Max sequence length** | Slider 512-4096: lunghezza massima delle sequenze in token (default: 512 per CPU, 2048+ per GPU) |
| **🏋️ Addestra (LoRA)** | Pulsante per avviare il training LoRA. Mostra log in tempo reale nella textbox "Log". |

### Stato

| Elemento | Descrizione |
|----------|-------------|
| **📊 Stato** | Pulsante che mostra statistiche correnti: numero entry nel dataset distillato, file modello LoRA, configurazione Teacher attiva. |
| **Log** | Textbox di output (20 righe, scrollabile fino a 40) che mostra in tempo reale i log della generazione e del training. |

### Persistenza

I profili personalizzati vengono salvati in `config/distill_profiles.json` (formato JSON, UTF-8).
La configurazione attiva del Teacher viene salvata in `config/teacher_config.yaml`.
Le API key **non** vengono mai salvate nei profili per ragioni di sicurezza.

---

## Tab 5: Dati

### Dataset Viewer

Visualizza il contenuto di `data/kb/dataset_unified.jsonl` con:

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

# Wiki Grafo Interattivo — Tutorial

## Cos'è

Il Wiki Grafo è una mappa concettuale interattiva che visualizza le relazioni tra componenti hardware, registri, istruzioni e concetti del Commodore 64. Ogni nodo è un termine C64 cliccabile, ogni arco rappresenta una relazione funzionale.

## Accesso

Il grafo è integrato nella UI Gradio del C64 Coding Assistant. Si trova nel tab **Wiki Grafo** (`http://localhost:7860`). Viene renderizzato lato server come SVG con logica JS embedded.

## Struttura del Grafo

### Nodi

87 nodi organizzati per categorie (colore):

| Categoria | Colore | Esempi |
|-----------|--------|--------|
| `chip` | Rosso | VIC-II, SID, CIA, CPU 6510 |
| `software` | Verde acqua | KERNAL, BASIC ROM |
| `concetto` | Azzurro | Memory Map, Sprite, Raster Interrupt |
| `registro` | Arancio | $D020, $D012, $D400 |
| `opcode` | Viola | LDA, STA, JMP, ADC |
| `basic` | Verde | POKE, PEEK, SYS, PRINT |

### Gruppi multilivello

7 gruppi collassabili/espandibili racchiudono nodi correlati:

| Gruppo | Membri | Categoria |
|--------|--------|-----------|
| **Opcode 6502** | 30 istruzioni (LDA, STA, ADC, JMP…) | opcode |
| **Chip C64** | VIC-II, SID, CIA, CPU 6510 | chip |
| **Reg. VIC-II** | 15 registri ($D020-$D024, $D011…) | registro |
| **Reg. SID** | 5 registri ($D400, $D404…) | registro |
| **Reg. CIA** | 3 registri ($DC00, $DC01, $DD00) | registro |
| **Vett. KERNAL** | 5 vettori ($FFD2, $FFE4…) | registro |
| **Comandi BASIC** | POKE, PEEK, SYS, PRINT | basic |

### Archi

105 archi con etichette come `legge`, `scrive`, `controlla`, `usa`, `attiva`. Le etichette **non appaiono** sul grafo per non appesantirlo; vengono mostrate nella **mappa connessioni** sotto la descrizione quando clicchi un nodo.

## Interazione

### Click su nodo libero

Mostra descrizione + mappa connessioni sotto il grafo.

### Click su gruppo collassato

Mostra descrizione del gruppo.

### Click su gruppo espanso

Richiede il gruppo.

### Doppio click su gruppo

Toggle espandi/comprimi (scorciatoia).

### Pan

Click + trascina (cambia il cursore in `grabbing`).

### Zoom

Rotellina del mouse. Zoom centrato sulla posizione del mouse. Scala tutto uniformemente (font, linee, cerchi).

### Toolbar

| Pulsante | Azione |
|----------|--------|
| ▲ Comprimi tutti | Chiude tutti i gruppi espansi |
| ▼ Espandi tutti | Apre tutti i gruppi |
| ↺ Reset vista | Resetta zoom/pan e chiude tutto |

## Architettura Tecnica

### Generazione SVG

Funzione `render_wiki_graph_svg()` in `agent/agent_pro.py` (~linea 1608):

1. Carica `data/wiki_graph.json` (87 nodi, 105 archi)
2. Calcola layout con `networkx.kamada_kawai_layout()`
3. Trasforma coordinate in spazio SVG (960×640)
4. Genera SVG con:
   - `<g id="wiki-viewport">` wrapper per zoom/pan via `transform`
   - Edges come `<line>` con classi per visibilità
   - Proxy edges (gruppo → esterno) tratteggiati
   - Nodi gruppo come pillole arrotondate con bordo tratteggiato
   - Nodi membri nascosti per default
   - Legenda in basso a sinistra
5. Embed JSON: nodi (`#wiki-nodes-data`), gruppi (`#wiki-groups-data`), archi (`#wiki-edges-data`)

### Bootstrap JS

A causa di Gradio 4.x che non esegue `<script>` inline con `innerHTML`, il JS è attivato con un `<img onerror>`:

```html
<img src=x onerror="(function(){ try{ … }catch(e){console.error(e)} })()">
```

Tutte le funzioni sono esposte su `window.*` (es. `window.showNode`, `window.toggleGroup`) per essere chiamabili da handler inline `onclick=""`.

### Zoom/Pan

Implementato via attributo `transform` sul wrapper `<g id="wiki-viewport">`:

```javascript
vp.setAttribute('transform',
  'translate(' + tx + ',' + ty + ') scale(' + scale + ')');
```

Vantaggio rispetto a modificare `viewBox`: il font scala uniformemente con tutto il resto.

### Visibilità Gruppi

`renderGroup(gid)` gestisce tre stati per gruppo:

- **Collassato**: pillola gruppo visibile, membri nascosti, proxy edges visibili
- **Espanso**: pillola gruppo nascosta, membri visibili, edges interni visibili
- La visibilità degli edge dipende anche dallo stato di altri gruppi (edge tra membri di due gruppi diversi mostrato solo se entrambi espansi)

### Mappa Connessioni

Quando clicchi un nodo, `showConnections(id)` cerca in `EDGES` tutti gli archi collegati e mostra: `→ NOME [etichetta]` o `← NOME [etichetta]`. Se il nodo non ha archi, la sezione si nasconde.

## Dati

### `data/wiki_graph.json`

```json
{
  "nodes": [
    {"id": "vic-ii", "label": "VIC-II", "category": "chip",
     "description": "Video Interface Chip II: il chip grafico del C64..."},
    ...
  ],
  "edges": [
    {"from": "vic-ii", "to": "raster-interrupt", "label": "genera"},
    {"from": "vic-ii", "to": "$D012", "label": "legge"},
    ...
  ]
}
```

### Aggiungere un nodo

1. Aggiungi al `data/wiki_graph.json` nella sezione `nodes`
2. Assegna una `category` esistente (`chip`, `software`, `concetto`, `registro`, `opcode`, `basic`)
3. Se appartiene a un gruppo, aggiungi l'ID alla lista `members` del gruppo in `agent/agent_pro.py` (sezione `GROUPS`)

### Aggiungere un gruppo

1. Definisci il gruppo in `GROUPS` dentro `render_wiki_graph_svg()` con `id`, `label`, `category`, `desc`, `members`
2. Il colore è ereditato dalla `category`

## Vincoli Importanti

1. **Niente `:` nelle classi CSS**: i selettori con due punti vengono interpretati come pseudo-classi. Usare attributi `data-group="..."` con virgolette.
2. **No `<script>` inline**: usare `<img onerror>` per bootstrap JS.
3. **Handler inline funzionano**: `onclick="fn()"` su elementi SVG funziona con innerHTML.
4. **`addEventListener` con flag `_bound`**: per evitare doppia attach dopo re-render del grafo.
5. **F-strings Python con doppie `{{`**: il JS usa `{` e `}`, in f-string vanno scritte come `{{` e `}}`.

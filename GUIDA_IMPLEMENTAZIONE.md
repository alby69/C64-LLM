# Guida all'Implementazione: C64 Intelligence SDK

Segui questi passi per trasformare i tuoi repository separati nel nuovo ecosistema integrato.

## Passo 1: Creazione del Repository Aggregatore
Crea un nuovo repository su GitHub chiamato `C64-Intelligence-SDK` e clonalo localmente.

```bash
mkdir C64-Intelligence-SDK
cd C64-Intelligence-SDK
git init
```

## Passo 2: Aggiunta dei Submodule
Collega i tuoi tre repository esistenti come sottomoduli. Questo permetterà di gestirli come cartelle indipendenti ma collegate.

```bash
git submodule add https://github.com/alby69/C64-LLM core
git submodule add https://github.com/alby69/PYC64 tools
git submodule add https://github.com/alby69/C64GameTutorial tutorial
```

## Passo 3: Configurazione dell'Ambiente Integrato
Copia il file `docker-compose.integration.yml` (che ho creato per te) nella root del nuovo repository e rinominalo in `docker-compose.yml`.

Crea anche la cartella per i plugin:
```bash
mkdir plugins
```

## Passo 4: Espansione della Conoscenza (RAG)
Per far sì che l'LLM impari dai tuoi tutorial, dobbiamo dire al core di leggere anche quella cartella.
Modifica il file `config/agent_config.yaml` all'interno della cartella `core/` (o usa un volume nel docker-compose) per includere il percorso dei tutorial:

```yaml
# Esempio di modifica (logica)
rag:
  additional_knowledge_paths:
    - "/app/tutorial"
```

## Passo 5: Creazione dei primi "Tools"
Prendi spunto dal file `examples/plugins/pyc64_integration.py` e crea i tuoi wrapper in `plugins/`.
Ogni volta che vuoi esporre una funzione di `PYC64` all'assistente:
1. Importa la funzione da `tools.pyc64`.
2. Decorala (o registrala) nel sistema degli agenti di `core`.

## Passo 6: Avvio
Ora puoi avviare tutto l'ecosistema con un solo comando:

```bash
docker-compose up --build
```

---
### Manutenzione
Per aggiornare tutti i componenti all'ultima versione disponibile sui rispettivi repo:
```bash
git submodule update --remote --merge
```

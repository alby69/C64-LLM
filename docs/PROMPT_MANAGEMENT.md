# Prompt Management System (PMS)

Il `PromptManagementSystem` (PMS) è il componente incaricato di centralizzare, versionare e gestire tutti i prompt utilizzati dagli agenti.

## Architettura

Tutti i prompt sono memorizzati in `prompts/prompts.yaml`. Questo approccio offre diversi vantaggi:
1. **Nessun Hardcoding**: I prompt non sono sparsi nel codice Python, rendendoli più facili da manutenere.
2. **Templating**: Utilizziamo **Jinja2** per iniettare variabili dinamiche nei prompt (es. i log di errore nel self-healing).
3. **Disaccoppiamento**: Gli agenti non sanno *cosa* dice il prompt, sanno solo *come* richiederlo via `PromptManager`.

## Come Usarlo

### Aggiungere un Prompt
Modifica `data/prompts/prompts.yaml`:
```yaml
categoria:
  subcategoria:
    chiave: >
      Il tuo testo del prompt qui.
      Puoi usare {{ variabile }} per dati dinamici.
```

### Richiamare un Prompt nel Codice
```python
from utils.prompt_manager import PromptManager
pm = PromptManager()

# Prompt statico
system_prompt = pm.get_prompt("categoria.subcategoria.chiave")

# Prompt dinamico (template)
user_prompt = pm.get_prompt("categoria.template", nome="Utente")
```

## Evoluzioni Future

1. **Prompt Versioning**: Gestire diverse versioni dello stesso prompt per test A/B tra diversi modelli (es. Qwen vs Phi).
2. **Dynamic Autocomplete**: Alimentare la UI di Gradio direttamente dal file YAML per suggerire all'utente i prompt più efficaci.
3. **Ottimizzazione Automatica**: Un agente "Prompt Engineer" potrebbe analizzare i log di successo/fallimento e suggerire modifiche al file YAML.

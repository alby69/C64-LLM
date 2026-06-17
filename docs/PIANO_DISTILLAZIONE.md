# Piano di Knowledge Distillation per C64 Coding Agent

> Trasformare Qwen2.5-Coder-1.5B in uno specialista C64 via Teacher→Student distillation.

---

## 1. Visione generale

Oggi Qwen 1.5B usa la RAG per rispondere: il contesto tecnico viene iniettato nel prompt ad ogni domanda. Il modello **non impara** nulla — dipende interamente dal retrieval.

Con la distillazione, il modello piccolo **assorbe** la conoscenza nei suoi pesi tramite training:

```
PRIMA (solo RAG):
  KB Chunk → Prompt → Qwen 1.5B → Risposta
  (il modello non impara mai)

DOPO (RAG + LoRA):
  Teacher LLM → Dataset sintetico → LoRA → Qwen 1.5B specializzato
  (il modello ha conoscenza interna + RAG come rinforzo)
```

## 2. Architettura implementata

### Componenti creati

| File | Ruolo |
|------|-------|
| `pipeline/knowledge_distiller.py` | Orchestratore: Teacher backends + generazione dataset + chunk loader |
| `config/teacher_config.yaml` | Configurazione Teacher (backend, modello, strategia) |
| `prompts/distill_prompts.yaml` | Template per ogni tipo di dato sintetico |
| `data/output/distill_dataset.jsonl` | Dataset generato (55+ QA pairs, copre tutte le KB) |

### Componenti modificati

| File | Modifica |
|------|----------|
| `pipeline/train_lora.py` | Validation split automatico, eval_strategy, max_seq_length=2048, load_best_model_at_end |
| `config/agent_config.yaml` | Aggiunta sezione `teacher:` |
| `run_pipeline.py` | Aggiunto step `04_distillation` |

## 3. Teacher: scelta e configurazione

Il Teacher predefinito è **OpenCode** (big-pickle, l'assistente che ti sta rispondendo). Ho già generato il primo dataset.

### Backend Teacher disponibili

| Backend | Classe | Free? | Modello default |
|---------|--------|-------|----------------|
| `opencode` | `OpenCodeTeacher` | ✅ | big-pickle (assistente) |
| `groq` | `GroqTeacher` | ✅ | `llama3-70b-8192` |
| `openrouter` | `OpenRouterTeacher` | ~$1-3 | `qwen/qwen3-32b` |
| `ollama` | `OllamaTeacher` | ✅ locale | `qwen3:32b` |
| `huggingface` | `HuggingFaceTeacher` | ✅ free tier | `Qwen/Qwen3-32B-Instruct` |

### Config

```yaml
# config/teacher_config.yaml
teacher:
  type: "opencode"
  strategy:
    types: ["factual", "code", "explain", "bugfix", "theory"]
    qa_per_chunk: 2
    languages: ["it", "en"]
```

## 4. Student: Qwen2.5-Coder-1.5B-Instruct

| Parametro | Valore |
|-----------|--------|
| Modello base | `Qwen/Qwen2.5-Coder-1.5B-Instruct` |
| Tecnica | LoRA (r=16, alpha=32, dropout=0.05) |
| Quantizzazione | 4-bit NF4 |
| Max seq length | 2048 (default, configurabile fino a 4096) |
| Batch | 2 per device, gradient accumulation 4 (effective batch 8) |
| Ottimizzatore | paged_adamw_32bit |
| Training | 200 step max, eval ogni 20 step, save ogni 20 step |
| Validation | 10% auto-split con load_best_model_at_end |
| Output | `data/models/c64-lora-pro/` |

## 5. Dataset generato (Teacher = OpenCode)

### Copertura

| KB File | # QA pairs | Tipi |
|---------|-----------|------|
| c64_memory_map.md | 7 | factual, code, explain |
| vic2_registers.md | 10 | factual, code, explain, bugfix |
| sprite_programming.md | 9 | factual, code, explain, bugfix |
| sid_programming.md | 9 | factual, code, explain |
| raster_interrupts.md | 7 | explain, code, bugfix |
| 6502_addressing_modes.md | 9 | factual, explain, code, bugfix |
| c64_basic_tutorial.md | 14 | factual, explain, code, bugfix |
| c64_screen_routines.md | 6 | factual, code, explain, bugfix |
| c64_cia_chips.md | 4 | factual, explain, code |
| kernal_routines.md | 6 | factual, explain, code, bugfix |

### Tipologia

| Tipo | Quantità | Scopo |
|------|----------|-------|
| Factual Q&A | ~12 | Conoscenza precisa (indirizzi, registri) |
| Code Generation | ~16 | Scrivere codice funzionante |
| Code Explanation | ~16 | Ragionamento passo-passo |
| Bug Fixing | ~10 | Debugging e correzione errori |
| Theory | ~4 | Concetti fondamentali |

Lingue: italiano (~70%) e inglese (~30%).

## 6. Come usare

### Addestrare Qwen con il dataset già generato

```bash
python pipeline/train_lora.py data/output/distill_dataset.jsonl
```

Il training:
1. Carica Qwen2.5-Coder-1.5B-Instruct in 4-bit
2. Applica LoRA (r=16)
3. Suddivide automaticamente 90% train / 10% validation
4. Addestra per 1000 step, salvando il miglior checkpoint
5. Salva in `data/models/c64-lora-pro/`

### Generare più dati con Teacher automatico

```bash
# Con Groq (gratuito, veloce)
export TEACHER_API_KEY="gsk_..."
python pipeline/knowledge_distiller.py --teacher groq --generate --max-chunks 200

# Con OpenRouter
export TEACHER_API_KEY="sk-or-..."
python pipeline/knowledge_distiller.py --teacher openrouter --model qwen/qwen3-32b --generate

# Con Ollama locale
python pipeline/knowledge_distiller.py --teacher ollama --model qwen3:32b --generate
```

### Generare più dati con me (OpenCode Teacher)

Basta chiedermelo — leggo la KB e genero nuove QA pairs per espandere il dataset.

## 7. Cosa cambia dopo distillazione

| Situazione | Con solo RAG | Con LoRA + RAG |
|------------|-------------|----------------|
| Senza RAG | Scarsa | **Buona** |
| Con RAG buona | Buona | **Ottima** |
| RAG sbagliata | Pessima | **Discreta** (modello corregge) |

Il modello specializzato:
- Conosce la terminologia C64 nei pesi
- Risponde senza bisogno di contesto KB per domande comuni
- È più robusto a chunk di retrieval imperfetti
- Può comunque beneficiare della RAG per domande complesse

## 8. Estensioni future

- **Self-distilling loop**: usa Qwen+LoRA come Teacher a sua volta
- **Rejection sampling**: genera N risposte per domanda, tieni la migliore
- **Active learning**: Validator identifica chunk poco coperti, li prioritizza
- **Multi-Teacher ensemble**: Claude + GPT-4o + Qwen3-32B insieme
- **Errore sintetico avanzato**: genera volutamente codice con bug per insegnare debugging

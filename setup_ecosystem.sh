#!/bin/bash

# Script di Setup automatico per C64 Intelligence Ecosystem
# Questo script prepara la struttura del nuovo repository SDK.

echo "--- Inizio Setup C64 Intelligence Ecosystem ---"

# 1. Creazione struttura cartelle
echo "Creazione struttura cartelle..."
mkdir -p plugins data/models data/output

# 2. Inizializzazione Git se necessario
if [ ! -d ".git" ]; then
    echo "Inizializzazione repository Git..."
    git init
fi

# 3. Messaggio per i Submodule (richiede interazione utente/rete)
echo ""
echo "PROSSIMO PASSO: Eseguire i comandi per aggiungere i submodule:"
echo "git submodule add https://github.com/alby69/C64-LLM core"
echo "git submodule add https://github.com/alby69/PYC64 tools"
echo "git submodule add https://github.com/alby69/C64GameTutorial tutorial"
echo ""

# 4. Copia file di configurazione se presenti (simulazione)
if [ -f "docker-compose.integration.yml" ]; then
    echo "Configurazione Docker Compose rilevata. Pronto per l'integrazione."
fi

# 5. Suggerimento download modello
echo "Ricorda di scaricare il modello GGUF in data/models/ se non presente."
echo "Esempio: wget -O data/models/qwen2.5-coder-1.5b.Q4_K_M.gguf https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"

echo "--- Setup Preliminare Completato ---"

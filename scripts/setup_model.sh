#!/usr/bin/env bash
# setup_model.sh — scarica il modello GGUF richiesto da C64-LLM (H2)
# con verifica del checksum. Uso: bash scripts/setup_model.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(dirname "$SCRIPT_DIR")"
MODEL_DIR="$CORE_DIR/data/models"
MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf}"
MODEL_FILE="qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
# SHA256 aggiornato al momento della release; verificare e aggiornare al bump.
MODEL_SHA256="${MODEL_SHA256:-}"

mkdir -p "$MODEL_DIR"
TARGET="$MODEL_DIR/$MODEL_FILE"

if [[ -f "$TARGET" ]]; then
  echo "[OK] Modello già presente: $TARGET"
  exit 0
fi

echo "[C64] Download $MODEL_URL"
wget -O "$TARGET" "$MODEL_URL"

if [[ -n "$MODEL_SHA256" ]]; then
  echo "[C64] Verifica checksum..."
  echo "$MODEL_SHA256  $TARGET" | sha256sum -c - || {
    echo "[ERROR] Checksum non valido; rimuovo il file corrotto" >&2
    rm -f "$TARGET"
    exit 1
  }
  echo "[OK] Checksum verificato"
else
  echo "[C64] Nessun checksum configurato: impostare MODEL_SHA256 per la verifica"
fi

echo "[OK] Modello pronto: $TARGET"
echo "[C64] Imposta in config/agent_config.yaml: gguf.path = data/models/$MODEL_FILE"
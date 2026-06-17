# =========================================
# C64 AI TRAINING PRO (16GB RAM Optimized)
# =========================================
import os
import sys
import json
import traceback
import torch
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, PeftModel
from trl import SFTTrainer, SFTConfig

# =========================
# CONFIG
# =========================
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
DATASET_PATH = (
    sys.argv[1] if len(sys.argv) > 1 else "./data/output/dataset_unified.jsonl"
)
VAL_DATASET_PATH = sys.argv[2] if len(sys.argv) > 2 else None
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/models/c64-lora-pro")
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "2048"))

print(f"MODEL_NAME={MODEL_NAME}", flush=True)
print(f"DATASET_PATH={DATASET_PATH}", flush=True)
print(f"OUTPUT_DIR={OUTPUT_DIR}", flush=True)
print(f"MAX_SEQ_LENGTH={MAX_SEQ_LENGTH}", flush=True)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# PROMPT FORMAT
# =========================
def format_example(example):
    instruction = example.get("instruction", "")
    context = example.get("context", "")
    input_text = example.get("input", "")
    output = example.get("output", "")

    prompt = f"<|im_start|>system\nSei un esperto programmatore per Commodore 64. {context}<|im_end|>\n"
    prompt += f"<|im_start|>user\n{instruction}\n"
    if input_text:
        prompt += f"Input:\n{input_text}\n"
    prompt += "<|im_end|>\n"
    prompt += f"<|im_start|>assistant\n{output}<|im_end|>"

    return {"text": prompt}


try:
    # =========================
    # LOAD TOKENIZER
    # =========================
    print("Caricamento tokenizer...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # =========================
    # LOAD MODEL (4-bit Quantization)
    # =========================
    print("Caricamento modello in 4-bit...", flush=True)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # =========================
    # LoRA CONFIG
    # =========================
    print("Configurazione LoRA...", flush=True)
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # =========================
    # LOAD DATASET
    # =========================
    print(f"Caricamento dataset da {DATASET_PATH}...", flush=True)
    dataset = load_dataset("json", data_files=DATASET_PATH)["train"]
    print(f"Dataset caricato: {len(dataset)} esempi", flush=True)
    dataset = dataset.map(format_example)
    print("Dataset formattato (esempi -> prompt)", flush=True)

    # Validation set
    eval_dataset = None
    if VAL_DATASET_PATH and os.path.exists(VAL_DATASET_PATH):
        eval_dataset = load_dataset("json", data_files=VAL_DATASET_PATH)["train"]
        eval_dataset = eval_dataset.map(format_example)
        print(
            f"Train: {len(dataset)} esempi | Val: {len(eval_dataset)} esempi",
            flush=True,
        )
    else:
        split = dataset.train_test_split(test_size=0.1, seed=42)
        dataset = split["train"]
        eval_dataset = split["test"]
        print(
            f"Train: {len(dataset)} esempi | Val (auto-split 10%): {len(eval_dataset)} esempi",
            flush=True,
        )

    # =========================
    # TRAINING CONFIG
    # =========================
    print("Avvio training...", flush=True)
    training_args = SFTConfig(
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=200,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=5,
        eval_strategy="steps",
        eval_steps=20,
        save_strategy="steps",
        save_steps=20,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        output_dir=OUTPUT_DIR,
        optim="paged_adamw_32bit",
        report_to="none",
        max_length=MAX_SEQ_LENGTH,
        dataset_text_field="text",
    )

    # =========================
    # TRAINER
    # =========================
    trainer = SFTTrainer(
        model=model,
        peft_config=lora_config,
        train_dataset=dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        args=training_args,
    )

    # =========================
    # TRAIN
    # =========================
    trainer.train()
    print("Training completato!", flush=True)

    # =========================
    # SAVE
    # =========================
    print(f"Salvataggio modello in {OUTPUT_DIR}...", flush=True)
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)

    saved_files = os.listdir(OUTPUT_DIR)
    print(f"File salvati ({len(saved_files)}): {saved_files}", flush=True)

    has_adapter = os.path.exists(os.path.join(OUTPUT_DIR, "adapter_config.json"))
    has_weights = os.path.exists(
        os.path.join(OUTPUT_DIR, "adapter_model.safetensors")
    ) or os.path.exists(os.path.join(OUTPUT_DIR, "adapter_model.bin"))
    if has_adapter and has_weights:
        print(f"✅ LoRA salvato correttamente in {OUTPUT_DIR}", flush=True)
    else:
        print(f"⚠️ ATTENZIONE: file LoRA mancanti in {OUTPUT_DIR}!", flush=True)
        print(f"  adapter_config.json: {has_adapter}", flush=True)
        print(f"  adapter_model.*: {has_weights}", flush=True)

except Exception:
    traceback.print_exc(file=sys.stdout)
    sys.exit(1)

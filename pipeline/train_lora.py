# =========================================
# C64 AI TRAINING PRO (16GB RAM Optimized)
# =========================================
import os
import sys
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer

# =========================
# CONFIG
# =========================
# Using Qwen2.5-Coder-1.5B-Instruct as a base: very powerful for its size and fits easily in 16GB RAM
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
DATASET_PATH = sys.argv[1] if len(sys.argv) > 1 else "./data/output/dataset_unified.jsonl"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/models/c64-lora-pro")

# =========================
# LOAD TOKENIZER
# =========================
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

# =========================
# LOAD MODEL (4-bit Quantization)
# =========================
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
    trust_remote_code=True
)

model = prepare_model_for_kbit_training(model)

# =========================
# LoRA CONFIG
# =========================
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# =========================
# PROMPT FORMAT
# =========================
def format_example(example):
    instruction = example.get('instruction', '')
    context = example.get('context', '')
    input_text = example.get('input', '')
    output = example.get('output', '')

    prompt = f"<|im_start|>system\nSei un esperto programmatore per Commodore 64. {context}<|im_end|>\n"
    prompt += f"<|im_start|>user\n{instruction}\n"
    if input_text:
        prompt += f"Input:\n{input_text}\n"
    prompt += "<|im_end|>\n"
    prompt += f"<|im_start|>assistant\n{output}<|im_end|>"

    return {"text": prompt}

# =========================
# LOAD DATASET
# =========================
dataset = load_dataset("json", data_files=DATASET_PATH)["train"]
dataset = dataset.map(format_example)

# =========================
# TRAINING CONFIG
# =========================
training_args = TrainingArguments(
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_steps=50,
    max_steps=500,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    output_dir=OUTPUT_DIR,
    optim="paged_adamw_32bit",
    save_strategy="steps",
    save_steps=100,
    report_to="none"
)

# =========================
# TRAINER
# =========================
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=1024,
    tokenizer=tokenizer,
    args=training_args
)

# =========================
# TRAIN
# =========================
trainer.train()

# =========================
# SAVE
# =========================
trainer.model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print(f"Training completato! Modello salvato in {OUTPUT_DIR}")

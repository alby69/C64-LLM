# =========================================
# C64 AI MODEL PIPELINE PRO (CPU-optimized)
# =========================================
# pip install transformers datasets peft bitsandbytes accelerate trl gradio

import os
import sys
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

# =========================
# CONFIG
# =========================
MODEL_NAME = os.getenv("MODEL_NAME", "mistralai/Mistral-7B-v0.1")
DATASET_PATH = sys.argv[1] if len(sys.argv) > 1 else "./dataset_c64.json"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./c64-model")
FINAL_DIR = os.getenv("FINAL_DIR", "./final-c64-model")

# =========================
# LOAD TOKENIZER
# =========================
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

custom_tokens = [
    "LDA","STA","ADC","SBC","JMP","JSR","RTS",
    "$D020","$D021","$0400","$C000"
]
tokenizer.add_tokens(custom_tokens)

# =========================
# LOAD MODEL (CPU with 8-bit)
# =========================
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True,
    device_map="cpu"
)

model.resize_token_embeddings(len(tokenizer))

# =========================
# LoRA CONFIG
# =========================
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# =========================
# PROMPT FORMAT
# =========================
def format_example(example):
    return {
        "text": f"<s>[INST] Scrivi codice 6502 ottimizzato per C64, senza spiegazioni inutili.\\n{example['instruction']} [/INST]\\n{example['output']}</s>"
    }

# =========================
# LOAD DATASET
# =========================
dataset = load_dataset("json", data_files=DATASET_PATH)["train"]
dataset = dataset.map(format_example)

# =========================
# TRAINING CONFIG (CPU-optimized)
# =========================
training_args = TrainingArguments(
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    warmup_steps=20,
    max_steps=100,
    learning_rate=2e-4,
    fp16=False,
    logging_steps=10,
    output_dir=OUTPUT_DIR,
    optim="adamw_torch",
    save_strategy="steps",
    save_steps=50,
    dataloader_num_workers=0,
    remove_unused_columns=False
)

# =========================
# TRAINER
# =========================
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    dataset_text_field="text",
    tokenizer=tokenizer,
    args=training_args
)

# =========================
# TRAIN
# =========================
trainer.train()

# =========================
# SAVE LoRA MODEL
# =========================
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Training completato!")

# =========================
# MERGE LoRA
# =========================
model = model.merge_and_unload()
model.save_pretrained(FINAL_DIR)
tokenizer.save_pretrained(FINAL_DIR)

print("Modello finale salvato!")

# =========================================
# CHAT INTERFACE (CPU)
# =========================================
import gradio as gr

model = AutoModelForCausalLM.from_pretrained(
    FINAL_DIR,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True,
    device_map="cpu"
)

tokenizer = AutoTokenizer.from_pretrained(FINAL_DIR)

SYSTEM_PROMPT = "Scrivi solo codice assembly 6502 funzionante per Commodore 64. Nessuna spiegazione."

def generate(prompt):
    full_prompt = f"<s>[INST] {SYSTEM_PROMPT}\\n{prompt} [/INST]"
    inputs = tokenizer(full_prompt, return_tensors="pt")
    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.3,
        top_p=0.9
    )
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

iface = gr.Interface(
    fn=generate,
    inputs="text",
    outputs="text",
    title="C64 AI Assistant PRO (6502 + BASIC)"
)

iface.launch()

import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from agent.orchestrator import OrchestratorAgent
import gradio as gr

class C64CodingAgent:
    def __init__(self, base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct", lora_path=None):
        # Load model in 4-bit for inference on 16GB RAM
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )

        print(f"Loading base model: {base_model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

        if lora_path and os.path.exists(lora_path):
            print(f"Loading LoRA from: {lora_path}")
            self.model = PeftModel.from_pretrained(self.model, lora_path)

        self.orchestrator = OrchestratorAgent(self.model, self.tokenizer)

    def generate_response(self, user_input, use_rag=True):
        return self.orchestrator.process_request(user_input, use_rag=use_rag)

def launch_ui(lora_path=None):
    agent = C64CodingAgent(lora_path=lora_path)

    def chat(message, history, use_rag):
        return agent.generate_response(message, use_rag=use_rag)

    iface = gr.ChatInterface(
        chat,
        additional_inputs=[
            gr.Checkbox(label="Usa Knowledge Base (RAG)", value=True)
        ],
        title="C64 Coding Agent PRO",
        description="Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato."
    )
    iface.launch()

if __name__ == "__main__":
    import sys
    lora = sys.argv[1] if len(sys.argv) > 1 else None
    launch_ui(lora)

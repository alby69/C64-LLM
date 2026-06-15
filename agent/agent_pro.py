import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
from agent.orchestrator import OrchestratorAgent
from utils.prompt_manager import PromptManager
import gradio as gr

from agent.model_backend import ModelBackend, LlamaCppBackend

class C64CodingAgent:
    def __init__(self, base_model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct", lora_path=None, gguf_path=None):
        if gguf_path and os.path.exists(gguf_path):
            print(f"Loading GGUF model for CPU: {gguf_path}")
            self.backend = LlamaCppBackend(gguf_path)
            self.tokenizer = None
        else:
            # Load model in 4-bit for inference on 16GB RAM (Default if no GGUF)
            try:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                )

                print(f"Loading base model: {base_model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(
                    base_model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=True
                )

                if lora_path and os.path.exists(lora_path):
                    print(f"Loading LoRA from: {lora_path}")
                    model = PeftModel.from_pretrained(model, lora_path)

                self.backend = ModelBackend(model, self.tokenizer)
            except Exception as e:
                print(f"Error loading model with transformers: {e}")
                print("Falling back to CPU-only mode (Mock/GGUF placeholder if path missing)")
                self.backend = LlamaCppBackend(gguf_path)
                self.tokenizer = None

        self.orchestrator = OrchestratorAgent(self.backend, self.tokenizer)
        self.pm = PromptManager()

    def chat_wrapper(self, message, history, use_rag, max_attempts):
        # Converti la history di Gradio nel formato previsto dall'Orchestrator se necessario
        # Gradio history è [[user, bot], ...]
        formatted_history = []
        for user_msg, bot_msg in history:
            formatted_history.append({"role": "user", "content": user_msg})
            formatted_history.append({"role": "assistant", "content": bot_msg})

        try:
            response, sources = self.orchestrator.process_request(
                message,
                use_rag=use_rag,
                chat_history=formatted_history,
                max_attempts=int(max_attempts)
            )

            source_text = ""
            if sources:
                source_text = "\n\n**Fonti consultate:**\n" + "\n".join([f"- {s}" for s in set(sources)])

            return response + source_text
        except Exception as e:
            return f"❌ Errore durante l'elaborazione: {str(e)}"

def launch_ui():
    lora = os.environ.get("LORA_PATH")
    gguf = os.environ.get("GGUF_MODEL_PATH")

    agent = C64CodingAgent(lora_path=lora, gguf_path=gguf)
    pm = PromptManager()

    prompt_library = pm.get_prompt("ui.prompt_library")
    if not isinstance(prompt_library, list):
        prompt_library = [
            "Come posso cambiare il colore del bordo?",
            "Esegui un ciclo in BASIC..."
        ]

    with gr.Blocks(title="C64 Coding Agent PRO") as demo:
        gr.Markdown("# C64 Coding Agent PRO")
        gr.Markdown("Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato.")

        with gr.Row():
            with gr.Column(scale=4):
                chat_interface = gr.ChatInterface(
                    agent.chat_wrapper,
                    additional_inputs=[
                        gr.Checkbox(label="Usa Knowledge Base (RAG)", value=True),
                        gr.Slider(minimum=1, maximum=5, value=3, step=1, label="Tentativi Self-Healing")
                    ]
                )
            with gr.Column(scale=1):
                gr.Markdown("### Prompt Library")
                lib_dropdown = gr.Dropdown(choices=prompt_library, label="Snippet Comuni")
                lib_button = gr.Button("Usa Prompt")

                gr.Markdown("### Technical Terms")
                gr.Examples(
                    examples=["$D020", "VIC-II", "SID", "KERNAL", "Raster Interrupt"],
                    inputs=chat_interface.textbox
                )

        def fill_prompt(choice):
            return choice

        lib_button.click(fn=fill_prompt, inputs=lib_dropdown, outputs=chat_interface.textbox)

    demo.launch(server_name="0.0.0.0")

if __name__ == "__main__":
    launch_ui()

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
            self.model = None
            self.tokenizer = None
        else:
            # Load model in 4-bit for inference on 16GB RAM (Default if no GGUF)
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

            self.backend = ModelBackend(self.model, self.tokenizer)

    pm = PromptManager()
    # Carica la libreria di prompt comuni dal sistema di gestione prompt
    # Se non presente, usa dei default di fallback
    prompt_library = pm.get_prompt("ui.prompt_library")
    if isinstance(prompt_library, str): # Fallback se non trovato o errore
        prompt_library = [
            "Crea uno sprite...",
            "Imposta un interruzione IRQ...",
            "Carica un file dal disco...",
            "Cambia il colore dello schermo...",
            "Esegui un ciclo in BASIC..."
        ]

    with gr.Blocks(title="C64 Coding Agent PRO") as demo:
        gr.Markdown("# C64 Coding Agent PRO")
        gr.Markdown("Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato.")

        with gr.Row():
            with gr.Column(scale=4):
                chat_interface = gr.ChatInterface(
                    chat,
                    additional_inputs=[
                        gr.Checkbox(label="Usa Knowledge Base (RAG)", value=True)
                    ]
                )
            with gr.Column(scale=1):
                gr.Markdown("### Prompt Library")
                lib_dropdown = gr.Dropdown(choices=prompt_library, label="Snippet Comuni")
                lib_button = gr.Button("Usa Prompt")

                # Semplice sistema di autocompletamento concettuale
                gr.Markdown("### Technical Terms")
                gr.Examples(
                    examples=["$D020", "VIC-II", "SID", "KERNAL", "Raster Interrupt"],
                    inputs=chat_interface.textbox
                )

        def fill_prompt(choice):
            return choice

        lib_button.click(fn=fill_prompt, inputs=lib_dropdown, outputs=chat_interface.textbox)

    demo.launch()

if __name__ == "__main__":
    import sys
    lora = sys.argv[1] if len(sys.argv) > 1 else None
    gguf = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("GGUF_MODEL_PATH")

    agent = C64CodingAgent(lora_path=lora, gguf_path=gguf)

    def chat(message, history, use_rag):
        return agent.generate_response(message, use_rag=use_rag)

    pm = PromptManager()
    # Carica la libreria di prompt comuni dal sistema di gestione prompt
    # Se non presente, usa dei default di fallback
    prompt_library = pm.get_prompt("ui.prompt_library")
    if isinstance(prompt_library, str): # Fallback se non trovato o errore
        prompt_library = [
            "Crea uno sprite...",
            "Imposta un interruzione IRQ...",
            "Carica un file dal disco...",
            "Cambia il colore dello schermo...",
            "Esegui un ciclo in BASIC..."
        ]

    with gr.Blocks(title="C64 Coding Agent PRO") as demo:
        gr.Markdown("# C64 Coding Agent PRO")
        gr.Markdown("Esperto in Assembly 6502 e BASIC v2 con Knowledge Base integrato.")

        with gr.Row():
            with gr.Column(scale=4):
                chat_interface = gr.ChatInterface(
                    chat,
                    additional_inputs=[
                        gr.Checkbox(label="Usa Knowledge Base (RAG)", value=True)
                    ]
                )
            with gr.Column(scale=1):
                gr.Markdown("### Prompt Library")
                lib_dropdown = gr.Dropdown(choices=prompt_library, label="Snippet Comuni")
                lib_button = gr.Button("Usa Prompt")

                # Semplice sistema di autocompletamento concettuale
                gr.Markdown("### Technical Terms")
                gr.Examples(
                    examples=["$D020", "VIC-II", "SID", "KERNAL", "Raster Interrupt"],
                    inputs=chat_interface.textbox
                )

        def fill_prompt(choice):
            return choice

        lib_button.click(fn=fill_prompt, inputs=lib_dropdown, outputs=chat_interface.textbox)

    demo.launch()

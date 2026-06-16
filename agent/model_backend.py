import os
import torch
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

class ModelBackend:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.device = model.device if hasattr(model, 'device') else "cpu"

    def generate(self, prompt, max_new_tokens=512, temperature=0.3, top_p=0.9):
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.eos_token_id
            )

        return self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

class LlamaCppBackend:
    """Integrazione llama.cpp per GGUF su CPU."""
    def __init__(self, model_path):
        self.model_path = model_path
        if Llama and model_path and os.path.exists(model_path):
            print(f"Initializing Llama-cpp with {model_path}")
            self.llm = Llama(
                model_path=model_path,
                n_ctx=8192,
                n_threads=os.cpu_count(),
                verbose=False
            )
        else:
            print("Llama-cpp-python not installed or model path invalid. Using Mock mode.")
            self.llm = None

    def generate(self, prompt, max_new_tokens=512, temperature=0.3, top_p=0.9):
        if self.llm:
            output = self.llm(
                prompt,
                max_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=["<|im_end|>", "<|endoftext|>"]
            )
            return output['choices'][0]['text']

        return "ERROR: Llama-cpp backend not properly initialized. This is a mock response."

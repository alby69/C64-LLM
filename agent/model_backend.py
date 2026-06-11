import torch

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
    """Placeholder per futura integrazione llama.cpp per GGUF su CPU."""
    def __init__(self, model_path):
        self.model_path = model_path
        # Qui verrebbe inizializzato llama-cpp-python
        pass

    def generate(self, prompt, **kwargs):
        # Implementazione reale con llama-cpp-python
        return "Not implemented yet (requires llama-cpp-python)"

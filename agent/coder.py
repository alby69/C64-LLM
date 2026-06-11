import torch

class CoderAgent:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.system_prompt = (
            "Sei un esperto programmatore per Commodore 64. "
            "Il tuo compito è scrivere codice Assembly 6502 o BASIC v2 di alta qualità. "
            "Usa il contesto fornito per essere il più accurato possibile. "
            "Commenta il codice per spiegare cosa fa ogni parte."
        )

    def generate_code(self, user_query, context=""):
        """Genera codice basandosi sulla richiesta e sul contesto fornito dal Researcher."""
        full_prompt = f"<|im_start|>system\n{self.system_prompt}\n{context}<|im_end|>\n"
        full_prompt += f"<|im_start|>user\n{user_query}<|im_end|>\n"
        full_prompt += "<|im_start|>assistant\n"

        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.4, # Lower temperature for code generation
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return response

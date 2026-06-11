import torch

class CoderAgent:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.system_prompt = (
            "Sei un esperto programmatore per Commodore 64 specializzato in Assembly 6502 e BASIC v2. "
            "Segui rigorosamente questi passaggi:\n"
            "1. ANALISI: Analizza il contesto fornito e identifica gli indirizzi di memoria o le routine KERNAL necessarie.\n"
            "2. PIANIFICAZIONE: Descrivi brevemente l'algoritmo che intendi implementare.\n"
            "3. IMPLEMENTAZIONE: Scrivi il codice pulito, ben commentato e ottimizzato.\n"
            "4. REVISIONE: Verifica mentalmente che non ci siano errori comuni (es. dimenticare l'origine *= o l'RTS finale)."
        )

    def generate_code(self, user_query, context=""):
        """Genera codice basandosi sulla richiesta e sul contesto fornito dal Researcher."""
        # Se la query sembra complessa, abbassiamo la temperatura per massima precisione
        is_asm = any(kw in user_query.upper() for kw in ["ASM", "ASSEMBLY", "6502", "KERNAL"])
        temp = 0.2 if is_asm else 0.4

        full_prompt = f"<|im_start|>system\n{self.system_prompt}\n\nCONTESTO TECNICO RECUPERATO:\n{context}<|im_end|>\n"
        full_prompt += f"<|im_start|>user\n{user_query}<|im_end|>\n"
        full_prompt += "<|im_start|>assistant\n"

        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=temp,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return response

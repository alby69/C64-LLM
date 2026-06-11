import torch

class CoderAgent:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.system_prompt = (
            "Sei un esperto programmatore per Commodore 64. "
            "Il tuo compito è scrivere codice Assembly 6502 o BASIC v2 di alta qualità.\n"
            "Segui sempre questo schema di ragionamento:\n"
            "1. ANALISI: Comprendi i requisiti e identifica i registri C64 necessari.\n"
            "2. PIANIFICAZIONE: Descrivi i passi logici dell'algoritmo.\n"
            "3. IMPLEMENTAZIONE: Scrivi il codice commentato.\n"
            "4. REVISIONE: Verifica internamente la correttezza di indirizzi e opcodes.\n"
            "Usa il contesto fornito per evitare allucinazioni su indirizzi di memoria."
        )

    def generate_code(self, user_query, context="", temperature=0.3):
        """Genera codice basandosi sulla richiesta e sul contesto fornito dal Researcher."""

        # Se la query sembra richiedere BASIC, potremmo alzare leggermente la temperatura
        if "basic" in user_query.lower():
            temperature = 0.4

        full_prompt = f"<|im_start|>system\n{self.system_prompt}\n\nCONTESTO TECNICO:\n{context}<|im_end|>\n"
        full_prompt += f"<|im_start|>user\n{user_query}<|im_end|>\n"
        full_prompt += "<|im_start|>assistant\n"

        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1536, # Aumentato per CoT
                temperature=temperature,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        return response

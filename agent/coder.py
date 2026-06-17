from utils.prompt_manager import PromptManager
from agent.model_backend import ModelBackend


class CoderAgent:
    def __init__(self, model, tokenizer):
        if model is not None and hasattr(model, "generate"):
            self.backend = model
        elif model is not None:
            self.backend = ModelBackend(model, tokenizer)
        else:
            self.backend = None
        self.pm = PromptManager()
        self.system_prompt = self.pm.get_prompt("coder.base.system")

    def generate_code(self, user_query, context="", temperature=0.3):
        """Genera codice basandosi sulla richiesta e sul contesto fornito dal Researcher."""

        # Determina la personalità in base al contesto o alla query
        personality = ""
        if "basic" in user_query.lower() or "basic" in context.lower():
            temperature = 0.4
            personality = (
                "\nPERSONALITÀ: Sei un esperto di BASIC V2. "
                "Preferisci la sintassi standard C64. Evita comandi di versioni successive (BASIC 3.5/7.0). "
                "Usa soluzioni efficienti per la memoria (es. variabili corte, pochi spazi)."
            )
        elif (
            "assembly" in user_query.lower()
            or "asm" in user_query.lower()
            or "assembly" in context.lower()
        ):
            temperature = 0.2
            personality = (
                "\nPERSONALITÀ: Sei un programmatore professionista di Assembly 6502/6510. "
                "Il target è il MOS 6510 del C64. Usa la sintassi ACME Assembler. "
                "Ottimizza per cicli di clock e occupa meno memoria possibile."
            )

        full_prompt = f"<|im_start|>system\n{self.system_prompt}{personality}\n\nCONTESTO TECNICO:\n{context}<|im_end|>\n"
        full_prompt += f"<|im_start|>user\n{user_query}<|im_end|>\n"
        full_prompt += "<|im_start|>assistant\n"

        return self.backend.generate(
            full_prompt, max_new_tokens=768, temperature=temperature
        )

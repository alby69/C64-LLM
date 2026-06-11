from utils.prompt_manager import PromptManager
from agent.model_backend import ModelBackend

class CoderAgent:
    def __init__(self, model, tokenizer):
        if not isinstance(model, ModelBackend) and model is not None:
            self.backend = ModelBackend(model, tokenizer)
        else:
            self.backend = model
        self.pm = PromptManager()
        self.system_prompt = self.pm.get_prompt("coder.base.system")

    def generate_code(self, user_query, context="", temperature=0.3):
        """Genera codice basandosi sulla richiesta e sul contesto fornito dal Researcher."""

        # Determina la personalità in base al contesto o alla query
        personality = ""
        if "basic" in user_query.lower() or "basic" in context.lower():
            temperature = 0.4
            personality = "\nPERSONALITÀ: " + self.pm.get_prompt("coder.personalities.basic.system")
        elif "assembly" in user_query.lower() or "asm" in user_query.lower() or "assembly" in context.lower():
            temperature = 0.2
            personality = "\nPERSONALITÀ: " + self.pm.get_prompt("coder.personalities.assembly.system")

        full_prompt = f"<|im_start|>system\n{self.system_prompt}{personality}\n\nCONTESTO TECNICO:\n{context}<|im_end|>\n"
        full_prompt += f"<|im_start|>user\n{user_query}<|im_end|>\n"
        full_prompt += "<|im_start|>assistant\n"

        return self.backend.generate(
            full_prompt,
            max_new_tokens=1536,
            temperature=temperature
        )

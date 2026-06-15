from agent.knowledge_base import C64KnowledgeBase
from utils.prompt_manager import PromptManager
from agent.model_backend import ModelBackend

class ResearcherAgent:
    def __init__(self, model=None, tokenizer=None):
        self.kb = C64KnowledgeBase()
        if model is not None and hasattr(model, 'generate'):
            self.backend = model
        elif model is not None:
            self.backend = ModelBackend(model, tokenizer)
        else:
            self.backend = None
        self.pm = PromptManager()

    def expand_query(self, query, chat_history=None):
        """Espande la query dell'utente in termini tecnici C64 usando l'LLM."""
        if not self.backend:
            return query

        history_str = ""
        if chat_history:
            history_str = "\nCRONOLOGIA RECENTE:\n" + "\n".join([f"U: {h[0]}\nA: {h[1]}" for h in chat_history[-2:]])

        system_prompt = self.pm.get_prompt("researcher.expansion.system")
        prompt = (
            f"<|im_start|>system\n{system_prompt}{history_str}<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        expanded = self.backend.generate(prompt, max_new_tokens=50, temperature=0.1).strip()
        print(f"[Researcher] Query espansa: {expanded}")
        return expanded

    def detect_language(self, query):
        """Rileva se l'utente richiede BASIC o Assembly."""
        if not self.backend:
            return "both"

        system_prompt = self.pm.get_prompt("researcher.language_detection.system")
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        lang = self.backend.generate(prompt, max_new_tokens=10, temperature=0.1).strip().lower()
        return lang

    def generate_hyde_answer(self, query):
        """Genera una risposta ipotetica (HyDE) per migliorare il recupero."""
        if not self.backend:
            return query

        system_prompt = "Sei un esperto di Commodore 64. Genera un paragrafo tecnico ipotetico che descriva la soluzione o i registri necessari per la seguente richiesta. Non preoccuparti della precisione assoluta, focalizzati sui termini tecnici."
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        hyde_answer = self.backend.generate(prompt, max_new_tokens=150, temperature=0.3).strip()
        print(f"[Researcher] HyDE Answer generata.")
        return hyde_answer

    def research(self, query, chat_history=None, use_hyde=True):
        """Interroga il Knowledge Base per ottenere contesto pertinente."""
        # 1. Espansione della query (con supporto multi-turn)
        expanded_query = self.expand_query(query, chat_history=chat_history)

        # 2. Rilevamento linguaggio
        lang = self.detect_language(query)
        print(f"[Researcher] Linguaggio rilevato: {lang}")

        # 3. HyDE (opzionale)
        search_query = expanded_query
        if use_hyde:
            search_query = self.generate_hyde_answer(expanded_query)

        # 4. Ricerca vettoriale
        docs = self.kb.query(search_query)
        if not docs:
            # Se la query espansa fallisce, prova con l'originale
            docs = self.kb.query(query)

        if not docs:
            return "Nessuna informazione specifica trovata nel Knowledge Base."

        context = f"\nLinguaggio richiesto (rilevato): {lang}\n"
        context += "\nInformazioni dal Knowledge Base:\n"
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            context += f"--- Frammento {i+1} (Sorgente: {source}) ---\n{doc.page_content}\n"

        return context

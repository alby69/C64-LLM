import torch
from agent.knowledge_base import C64KnowledgeBase

class ResearcherAgent:
    def __init__(self, model=None, tokenizer=None):
        self.kb = C64KnowledgeBase()
        self.model = model
        self.tokenizer = tokenizer

    def _expand_query(self, user_query):
        """Usa l'LLM per espandere la query dell'utente in termini tecnici C64."""
        if not self.model or not self.tokenizer:
            return user_query

        prompt = (
            f"<|im_start|>system\nSei un esperto di Commodore 64. Trasforma la richiesta dell'utente in una lista di parole chiave tecniche, "
            f"indirizzi di memoria (se noti) e termini per la ricerca nel knowledge base (es. '6502 assembly', 'KERNAL routines', 'VIC-II registers').\n"
            f"Rispondi SOLO con i termini di ricerca ottimizzati.<|im_end|>\n"
            f"<|im_start|>user\nRichiesta: {user_query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(**inputs, max_new_tokens=50, temperature=0.1)

        expanded = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        print(f"[Researcher] Query espansa: {expanded}")
        return expanded

    def research(self, query):
        """Interroga il Knowledge Base con una query ottimizzata."""
        # 1. Espansione della query
        optimized_query = self._expand_query(query)

        # 2. Ricerca vettoriale
        docs = self.kb.query(optimized_query, k=5) # Aumentiamo a 5 per avere più varietà

        if not docs:
            return "Nessuna informazione specifica trovata nel Knowledge Base."

        # 3. Formattazione del contesto
        context = "\nInformazioni dal Knowledge Base (Ricerca ottimizzata):\n"
        for i, doc in enumerate(docs):
            # Aggiungiamo metadati se presenti (es. nome file)
            source = doc.metadata.get('source', 'Sconosciuta')
            context += f"--- Frammento {i+1} [Fonte: {source}] ---\n{doc.page_content}\n"

        return context

import torch
from agent.knowledge_base import C64KnowledgeBase

class ResearcherAgent:
    def __init__(self, model=None, tokenizer=None):
        self.kb = C64KnowledgeBase()
        self.model = model
        self.tokenizer = tokenizer

    def expand_query(self, query):
        """Espande la query dell'utente in termini tecnici C64 usando l'LLM."""
        if not self.model or not self.tokenizer:
            return query

        prompt = (
            f"<|im_start|>system\nSei un esperto tecnico del Commodore 64. "
            f"Traduci la richiesta dell'utente in parole chiave tecniche, registri VIC-II o SID, "
            f"e indirizzi di memoria rilevanti per migliorare la ricerca nel Knowledge Base.\n"
            f"Esempio: 'cambio colore bordo' -> '$D020, VIC-II, border color, register'\n"
            f"Rispondi SOLO con le parole chiave separate da virgola.<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        expanded = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
        print(f"[Researcher] Query espansa: {expanded}")
        return expanded

    def detect_language(self, query):
        """Rileva se l'utente richiede BASIC o Assembly."""
        if not self.model or not self.tokenizer:
            return "both"

        prompt = (
            f"<|im_start|>system\nClassifica se la richiesta dell'utente riguarda il linguaggio 'BASIC', 'Assembly' o 'entrambi'. "
            f"Rispondi solo con una di queste tre parole.<|im_end|>\n"
            f"<|im_start|>user\n{query}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=10,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        lang = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip().lower()
        return lang

    def research(self, query):
        """Interroga il Knowledge Base per ottenere contesto pertinente."""
        # 1. Espansione della query
        expanded_query = self.expand_query(query)

        # 2. Rilevamento linguaggio
        lang = self.detect_language(query)
        print(f"[Researcher] Linguaggio rilevato: {lang}")

        # 3. Ricerca vettoriale
        docs = self.kb.query(expanded_query)
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

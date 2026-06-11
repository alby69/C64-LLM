from agent.knowledge_base import C64KnowledgeBase

class ResearcherAgent:
    def __init__(self):
        self.kb = C64KnowledgeBase()

    def research(self, query):
        """Interroga il Knowledge Base per ottenere contesto pertinente."""
        docs = self.kb.query(query)
        if not docs:
            return "Nessuna informazione specifica trovata nel Knowledge Base."

        context = "\nInformazioni dal Knowledge Base:\n"
        for i, doc in enumerate(docs):
            context += f"--- Documento {i+1} ---\n{doc.page_content}\n"

        return context

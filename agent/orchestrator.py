import re
from agent.researcher import ResearcherAgent
from agent.coder import CoderAgent
from agent.validator import ValidatorAgent
from agent.memory_advisor import MemoryAdvisor
from utils.prompt_manager import PromptManager

class OrchestratorAgent:
    def __init__(self, model, tokenizer, pm=None):
        self.researcher = ResearcherAgent(model, tokenizer)
        self.coder = CoderAgent(model, tokenizer)
        self.validator = ValidatorAgent()
        self.pm = pm if pm else PromptManager()
        self.memory_advisor = MemoryAdvisor()

    def process_request(self, user_query, use_rag=True, chat_history=None, max_attempts=3):
        """Coordina il flusso di lavoro tra i vari agenti con multi-round self-healing."""
        logs = []

        # 1. Fase di Ricerca
        context = ""
        sources = []
        if use_rag:
            msg = "[Orchestrator] Avvio fase di ricerca (RAG + HyDE)..."
            print(msg)
            logs.append(msg)

            use_hyde = self.pm.get_config("rag.use_hyde", True)
            context = self.researcher.research(user_query, chat_history=chat_history, use_hyde=use_hyde)
            sources = re.findall(r"Sorgente: (.*?)\)", context)

        # Suggerimento proattivo della memoria (via MemoryAdvisor)
        lang = self.researcher.detect_language(user_query)
        mem_suggestion = self.memory_advisor.suggest_area(language=lang)

        # Check per sovrapposizioni critiche (vettori di sistema) via MemoryAdvisor
        system_collision = self.memory_advisor.check_collision(0x0314, 0x0315) # IRQ Vector
        collision_warning = ""
        if system_collision:
            collision_warning = f"\nATTENZIONE: Il codice precedente ha modificato i vettori di sistema ({system_collision}). Assicurati di gestire bene le interruzioni.\n"

        mem_context = f"\nMAPPA MEMORIA ATTUALE:\n{self.memory_advisor.get_summary()}\n{collision_warning}{mem_suggestion}\n"
        full_context_for_coder = context + mem_context

        # 2. Ciclo di Generazione e Validazione (Self-healing)
        current_query = user_query
        current_context = full_context_for_coder
        attempts = 0
        last_response = ""

        while attempts < max_attempts:
            attempts += 1
            msg = f"[Orchestrator] Tentativo {attempts} di generazione..."
            print(msg)
            logs.append(msg)

            response = self.coder.generate_code(current_query, current_context)
            last_response = response

            msg = f"[Orchestrator] Validazione del codice (Tentativo {attempts})..."
            print(msg)
            logs.append(msg)
            success, log = self.validator.validate(response)

            if success:
                self.memory_advisor.extract_from_code(response)
                final_response = response
                if attempts > 1:
                    final_response = f"Nota: Il codice è stato corretto dopo {attempts-1} tentativi.\n\n{response}"
                return final_response, sources, logs

            msg = f"[Orchestrator] Validazione fallita: {log}"
            print(msg)
            logs.append(msg)

            # Prepariamo la correzione per il prossimo round
            current_query = self.pm.get_prompt("orchestrator.self_healing.user_template", log=log)
            current_context = f"{full_context_for_coder}\n\nRisposta precedente errata:\n{response}"

        return f"Attenzione: Non è stato possibile generare codice valido dopo {max_attempts} tentativi.\n\nUltima versione generata:\n{last_response}\n\nErrori:\n{log}", sources, logs


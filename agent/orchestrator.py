from agent.researcher import ResearcherAgent
from agent.coder import CoderAgent
from agent.validator import ValidatorAgent
from utils.prompt_manager import PromptManager

class OrchestratorAgent:
    def __init__(self, model, tokenizer):
        self.researcher = ResearcherAgent(model, tokenizer)
        self.coder = CoderAgent(model, tokenizer)
        self.validator = ValidatorAgent()
        self.pm = PromptManager()

    def process_request(self, user_query, use_rag=True):
        """Coordina il flusso di lavoro tra i vari agenti."""

        # 1. Fase di Ricerca
        context = ""
        if use_rag:
            print("[Orchestrator] Avvio fase di ricerca...")
            context = self.researcher.research(user_query)

        # 2. Fase di Codifica
        print("[Orchestrator] Avvio generazione risposta/codice...")
        initial_response = self.coder.generate_code(user_query, context)

        # 3. Fase di Validazione
        print("[Orchestrator] Validazione del codice generato...")
        success, log = self.validator.validate(initial_response)

        if success:
            return initial_response
        else:
            # 4. Fase di Self-healing (opzionale - un tentativo di correzione)
            print(f"[Orchestrator] Validazione fallita. Tentativo di correzione...\nLog: {log}")
            correction_query = self.pm.get_prompt("orchestrator.self_healing.user_template", log=log)

            # Forniamo anche la risposta originale come contesto per la correzione
            full_context = f"{context}\n\nRisposta precedente errata:\n{initial_response}"
            corrected_response = self.coder.generate_code(correction_query, full_context)

            # Ri-validiamo
            print("[Orchestrator] Validazione del codice corretto...")
            success_fixed, log_fixed = self.validator.validate(corrected_response)

            if success_fixed:
                return f"Nota: Il primo tentativo conteneva errori, ecco la versione corretta:\n\n{corrected_response}"
            else:
                return f"Attenzione: Non è stato possibile generare codice valido dopo un tentativo di correzione.\n\nUltima versione generata:\n{corrected_response}\n\nErrori:\n{log_fixed}"

import re
from agent.researcher import ResearcherAgent
from agent.coder import CoderAgent
from agent.validator import ValidatorAgent
from utils.prompt_manager import PromptManager

class MemoryMapTracker:
    """Semplice tracker per la memoria del C64 per evitare collisioni."""
    def __init__(self):
        self.allocations = {} # {address_range: purpose}

    def add_allocation(self, start, end, purpose):
        self.allocations[f"{start:04X}-{end:04X}"] = purpose

    def get_summary(self):
        if not self.allocations:
            return "Nessuna allocazione registrata."
        return "\n".join([f"- {addr}: {purp}" for addr, purp in self.allocations.items()])

class OrchestratorAgent:
    def __init__(self, model, tokenizer):
        self.researcher = ResearcherAgent(model, tokenizer)
        self.coder = CoderAgent(model, tokenizer)
        self.validator = ValidatorAgent()
        self.pm = PromptManager()
        self.memory_tracker = MemoryMapTracker()

    def process_request(self, user_query, use_rag=True):
        """Coordina il flusso di lavoro tra i vari agenti."""

        # 1. Fase di Ricerca
        context = ""
        sources = []
        if use_rag:
            print("[Orchestrator] Avvio fase di ricerca...")
            context = self.researcher.research(user_query)
            # Estrarre le sorgenti per la UI (semplificato)
            sources = re.findall(r"Sorgente: (.*?)\)", context)

        # Aggiungi informazioni sulla memoria attuale al contesto
        mem_context = f"\nMAPPA MEMORIA ATTUALE:\n{self.memory_tracker.get_summary()}\n"
        full_context_for_coder = context + mem_context

        # 2. Fase di Codifica
        print("[Orchestrator] Avvio generazione risposta/codice...")
        initial_response = self.coder.generate_code(user_query, full_context_for_coder)

        # 3. Fase di Validazione
        print("[Orchestrator] Validazione del codice generato...")
        success, log = self.validator.validate(initial_response)

        # Estrarre eventuali allocazioni di memoria dal codice (euristica semplice)
        self._track_memory_from_code(initial_response)

        if success:
            return initial_response, sources
        else:
            # 4. Fase di Self-healing
            print(f"[Orchestrator] Validazione fallita. Tentativo di correzione...\nLog: {log}")
            correction_query = self.pm.get_prompt("orchestrator.self_healing.user_template", log=log)

            full_context = f"{full_context_for_coder}\n\nRisposta precedente errata:\n{initial_response}"
            corrected_response = self.coder.generate_code(correction_query, full_context)

            # Ri-validiamo
            print("[Orchestrator] Validazione del codice corretto...")
            success_fixed, log_fixed = self.validator.validate(corrected_response)

            if success_fixed:
                self._track_memory_from_code(corrected_response)
                return f"Nota: Il primo tentativo conteneva errori, ecco la versione corretta:\n\n{corrected_response}", sources
            else:
                return f"Attenzione: Non è stato possibile generare codice valido dopo un tentativo di correzione.\n\nUltima versione generata:\n{corrected_response}\n\nErrori:\n{log_fixed}", sources

    def _track_memory_from_code(self, text):
        """Tenta di estrarre direttive * = o numeri di riga BASIC per tracciare la memoria."""
        # Esempio Assembly: * = $1000
        asm_org = re.findall(r'\* = \$([0-9A-Fa-f]{4})', text)
        for addr in asm_org:
            start = int(addr, 16)
            self.memory_tracker.add_allocation(start, start + 0x100, "Codice/Dati Assembly")

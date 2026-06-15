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

    def _suggest_memory_area(self, user_query, context):
        """Suggerisce un'area di memoria libera basata sulla query."""
        if "basic" in user_query.lower() or "basic" in context.lower():
            return "Suggerimento: Per il BASIC v2, usa i numeri di riga standard (10, 20...). La memoria utente inizia a $0801."

        # Per Assembly, cerchiamo di suggerire $C000 o $1000 se non usati
        allocs = self.memory_tracker.get_summary()
        if "C000" not in allocs:
            return "Suggerimento: L'area $C000 (49152) è libera e spesso sicura per piccoli programmi Assembly."
        if "1000" not in allocs:
            return "Suggerimento: L'area $1000 (4096) è libera per il tuo codice Assembly."

        return "Suggerimento: Assicurati di dichiarare esplicitamente l'indirizzo di inizio con * = $XXXX."

    def process_request(self, user_query, use_rag=True, chat_history=None, max_attempts=3):
        """Coordina il flusso di lavoro tra i vari agenti con multi-round self-healing."""

        # 1. Fase di Ricerca
        context = ""
        sources = []
        if use_rag:
            print("[Orchestrator] Avvio fase di ricerca...")
            context = self.researcher.research(user_query, chat_history=chat_history)
            sources = re.findall(r"Sorgente: (.*?)\)", context)

        # Suggerimento proattivo della memoria
        mem_suggestion = self._suggest_memory_area(user_query, context)
        mem_context = f"\nMAPPA MEMORIA ATTUALE:\n{self.memory_tracker.get_summary()}\n{mem_suggestion}\n"
        full_context_for_coder = context + mem_context

        # 2. Ciclo di Generazione e Validazione (Self-healing)
        current_query = user_query
        current_context = full_context_for_coder
        attempts = 0
        last_response = ""

        while attempts < max_attempts:
            attempts += 1
            print(f"[Orchestrator] Tentativo {attempts} di generazione...")

            response = self.coder.generate_code(current_query, current_context)
            last_response = response

            print(f"[Orchestrator] Validazione del codice (Tentativo {attempts})...")
            success, log = self.validator.validate(response)

            if success:
                self._track_memory_from_code(response)
                if attempts > 1:
                    return f"Nota: Il codice è stato corretto dopo {attempts-1} tentativi.\n\n{response}", sources
                return response, sources

            print(f"[Orchestrator] Validazione fallita: {log}")

            # Prepariamo la correzione per il prossimo round
            current_query = self.pm.get_prompt("orchestrator.self_healing.user_template", log=log)
            current_context = f"{full_context_for_coder}\n\nRisposta precedente errata:\n{response}"

        return f"Attenzione: Non è stato possibile generare codice valido dopo {max_attempts} tentativi.\n\nUltima versione generata:\n{last_response}\n\nErrori:\n{log}", sources

    def _track_memory_from_code(self, text):
        """Tenta di estrarre direttive * = o numeri di riga BASIC per tracciare la memoria."""
        # Esempio Assembly: * = $1000 o *=$1000
        asm_org = re.findall(r'\*\s*=\s*\$([0-9A-Fa-f]{4})', text)
        for addr in asm_org:
            start = int(addr, 16)
            # Stimiamo 256 byte per ora se non sappiamo la fine,
            # ma potremmo migliorare analizzando tutto il blocco
            self.memory_tracker.add_allocation(start, start + 0xFF, "Codice/Dati Assembly")

        # BASIC: Numeri di riga (solo per segnalare occupazione area BASIC standard)
        if re.search(r'^\d+\s+', text, re.MULTILINE):
            self.memory_tracker.add_allocation(0x0801, 0x9FFF, "Programma BASIC")

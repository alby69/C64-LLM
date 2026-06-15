import re

class MemoryAdvisor:
    """Utility specializzata nella gestione e consulenza della memoria C64."""

    SYSTEM_VECTORS = {
        0x0314: "CINV (IRQ Vector)",
        0x0316: "CBINV (BRK Vector)",
        0x0318: "NMINV (NMI Vector)",
        0xFFFA: "NMI Vector (Hardware)",
        0xFFFC: "RESET Vector",
        0xFFFE: "IRQ/BRK Vector (Hardware)"
    }

    def __init__(self):
        self.allocations = [] # List of {start, end, purpose}

    def add_allocation(self, start, end, purpose):
        collision = self.check_collision(start, end)
        self.allocations.append({
            "start": start,
            "end": end,
            "purpose": purpose,
            "collision": collision
        })
        return collision

    def check_collision(self, start, end):
        # Controlla collisioni con allocazioni esistenti
        for alloc in self.allocations:
            if not (end < alloc["start"] or start > alloc["end"]):
                return f"${alloc['start']:04X}-${alloc['end']:04X} ({alloc['purpose']})"

        # Controlla collisioni con vettori di sistema
        for addr, name in self.SYSTEM_VECTORS.items():
            if start <= addr <= end:
                return f"${addr:04X} ({name})"

        return None

    def get_summary(self):
        if not self.allocations:
            return "Nessuna allocazione registrata."
        return "\n".join([f"- ${a['start']:04X}-${a['end']:04X}: {a['purpose']}" for a in self.allocations])

    def suggest_area(self, language="assembly"):
        if language.lower() == "basic":
            return "Suggerimento: Per il BASIC v2, la memoria utente inizia a $0801."

        # Suggerimenti per Assembly
        safe_areas = [0xC000, 0x1000, 0x2000, 0x4000]
        for area in safe_areas:
            if not self.check_collision(area, area + 0x0FFF):
                return f"Suggerimento: L'area ${area:04X} è libera e sicura per il codice Assembly."

        return "Suggerimento: Assicurati di dichiarare esplicitamente l'indirizzo di inizio con * = $XXXX."

    def extract_from_code(self, text):
        """Estrae direttive di memoria dal codice."""
        found = []
        # Assembly: * = $1000
        asm_org = re.findall(r'\*\s*=\s*\$([0-9A-Fa-f]{4})', text)
        for addr in asm_org:
            start = int(addr, 16)
            found.append((start, start + 0xFF, "Codice/Dati Assembly"))

        # BASIC: solo se rilevati numeri di riga
        if re.search(r'^\d+\s+', text, re.MULTILINE):
            found.append((0x0801, 0x9FFF, "Programma BASIC"))

        for start, end, purpose in found:
            self.add_allocation(start, end, purpose)

        return found

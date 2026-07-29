class InteractiveMemoryMap:
    """
    Rappresenta una mappa di memoria interattiva del Commodore 64 ($0000-$FFFF).
    Visualizza le zone colorate (ROM, RAM, I/O) e fornisce raccomandazioni o avvisi di collisione.
    """
    def __init__(self):
        # Mappa delle regioni principali con etichette, colori e range
        self.regions = [
            {"start": 0x0000, "end": 0x00FF, "name": "Zero Page", "color": "#ff4d4d", "desc": "Utilizzata intensamente dalla CPU 6510 e dal KERNAL per indirizzamento rapido e puntatori."},
            {"start": 0x0100, "end": 0x01FF, "name": "System Stack", "color": "#ff944d", "desc": "Stack di sistema della CPU. Evitare assolutamente di sovrascrivere."},
            {"start": 0x0200, "end": 0x03FF, "name": "System Vectors & Buffers", "color": "#ffff4d", "desc": "Buffer tastiera, vettori degli interrupt ($0314) e tabelle del sistema operativo."},
            {"start": 0x0400, "end": 0x07E7, "name": "Screen Memory", "color": "#4dff4d", "desc": "Memoria video di default (1024 caratteri). Viene visualizzata direttamente a schermo."},
            {"start": 0x07F8, "end": 0x07FF, "name": "Sprite Pointers", "color": "#4dffff", "desc": "Puntatori di blocco per gli 8 sprite gestiti dal VIC-II."},
            {"start": 0x0800, "end": 0x9FFF, "name": "BASIC RAM", "color": "#4d94ff", "desc": "Area RAM per programmi BASIC v2. Inizia a $0801 (SYS launcher)."},
            {"start": 0xA000, "end": 0xBFFF, "name": "BASIC ROM (or RAM)", "color": "#944dff", "desc": "Contiene l'interprete BASIC C64. Disattivabile per esporre la RAM sottostante."},
            {"start": 0xC000, "end": 0xCFFF, "name": "Free RAM (User Area)", "color": "#00ffcc", "desc": "4KB di RAM completamente libera per routine in codice macchina dell'utente."},
            {"start": 0xD000, "end": 0xDFFF, "name": "I/O Registers / Character ROM", "color": "#ff4d94", "desc": "Registri hardware VIC-II ($D000), SID ($D400), CIA 1 ($DC00), CIA 2 ($DD00)."},
            {"start": 0xE000, "end": 0xFFFF, "name": "KERNAL ROM (or RAM)", "color": "#b366ff", "desc": "Sistema operativo KERNAL del C64. Gestisce I/O, interrupt e chiamate di sistema."}
        ]

    def render_html_map(self):
        """Genera un grafico SVG/HTML della mappa di memoria con hover informativo."""
        blocks = []
        for reg in self.regions:
            size = reg["end"] - reg["start"] + 1
            # Normalizzazione logaritmica o proporzionale semplice della larghezza
            percentage = max(4.0, (size / 65536.0) * 100.0)

            blocks.append(f"""
            <div style="flex: {percentage:.2f}; background-color: {reg['color']}; height: 50px; border: 1px solid #111; position: relative; cursor: help;"
                 title="{reg['name']} (${reg['start']:04X}-${reg['end']:04X})&#10;{reg['desc']}"
                 onclick="alert('{reg['name']} (${reg['start']:04X}-${reg['end']:04X})\\n\\n{reg['desc']}')">
                <div style="font-size: 9px; text-align: center; color: #000; font-weight: bold; padding-top: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {reg['name']}
                </div>
            </div>
            """)

        legend_items = []
        for reg in self.regions:
            legend_items.append(f"""
            <div style="display: flex; align-items: center; margin-bottom: 6px; font-size: 13px;">
                <div style="width: 14px; height: 14px; background-color: {reg['color']}; border: 1px solid #000; margin-right: 8px; border-radius: 2px;"></div>
                <strong style="color: #ffffff; min-width: 180px;">{reg['name']}:</strong>
                <span style="color: #88ccff; margin-right: 10px;">${reg['start']:04X} - ${reg['end']:04X}</span>
                <span style="color: #ccc;">{reg['desc']}</span>
            </div>
            """)

        return f"""
        <div style="background-color: #1a1a2e; border: 3px solid #5a5ad6; border-radius: 8px; padding: 15px; font-family: monospace; color: #fff;">
            <h3 style="margin-top: 0; color: #00d2ff; border-bottom: 2px solid #5a5ad6; padding-bottom: 6px;">MAPPA MEMORIA C64 ($0000 - $FFFF)</h3>

            <p style="font-size: 13px; color: #bbb;">Visualizzazione proporzionale dell'architettura della RAM/ROM. Passa il mouse sopra o clicca su una sezione per maggiori dettagli.</p>

            <!-- Barra grafica proporzionale -->
            <div style="display: flex; width: 100%; border: 3px solid #fff; border-radius: 4px; overflow: hidden; margin: 20px 0; background-color: #000;">
                {"".join(blocks)}
            </div>

            <!-- Legenda descrittiva -->
            <div style="margin-top: 20px; border-top: 1px solid #333; padding-top: 15px;">
                {"".join(legend_items)}
            </div>

            <!-- Consigli per il posizionamento -->
            <div style="margin-top: 20px; background-color: #2a2a4e; border-left: 5px solid #00ffcc; padding: 12px; border-radius: 4px;">
                <h4 style="margin: 0 0 6px 0; color: #00ffcc;">🎯 INDIRIZZI CONSIGLIATI PER CODICE MACCHINA</h4>
                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #ddd; line-height: 1.5;">
                    <li><strong style="color: #fff;">$C000 - $CFFF (49152 - 53247):</strong> La zona migliore in assoluto. 4KB liberi non usati dal BASIC o dal KERNAL.</li>
                    <li><strong style="color: #fff;">$0340 - $03FF (832 - 1023):</strong> Zona libera da 192 byte, ideale per brevi routine di utility o vettori personalizzati.</li>
                    <li><strong style="color: #fff;">$1000 - $1FFF (4096 - 8191):</strong> RAM BASIC libera, se non si stanno usando programmi BASIC eccessivamente lunghi.</li>
                </ul>
            </div>
        </div>
        """

    def check_safety(self, address, size=1):
        """
        Verifica se un indirizzo e dimensione specificati entrano in collisione con zone critiche del sistema.
        """
        end_address = address + size - 1
        conflicts = []

        critical_regions = [
            {"start": 0x0000, "end": 0x00FF, "name": "Zero Page"},
            {"start": 0x0100, "end": 0x01FF, "name": "System Stack"},
            {"start": 0x0200, "end": 0x03FF, "name": "System Vectors"},
            {"start": 0x0400, "end": 0x07FF, "name": "Screen Memory / Sprite Pointers"},
            {"start": 0xD000, "end": 0xDFFF, "name": "Hardware I/O Registers"}
        ]

        for reg in critical_regions:
            # Verifica intersezione range
            if max(address, reg["start"]) <= min(end_address, reg["end"]):
                conflicts.append(reg["name"])

        if conflicts:
            return False, f"⚠️ ATTENZIONE: Il range di memoria richiesto (${address:04X} - ${end_address:04X}) si sovrappone a zone critiche del sistema: {', '.join(conflicts)}. Questo potrebbe causare crash, comportamenti imprevedibili o resettare la macchina."

        return True, "✅ Il range di memoria specificato è sicuro per l'uso."

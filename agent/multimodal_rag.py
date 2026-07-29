import os
import json
from utils.c64_graphics_extractor import extract_and_save_all_synthetic

class MultimodalRAG:
    """
    Gestisce l'indicizzazione, la ricerca e il reperimento di asset grafici C64 (sprite, charset, bitmap).
    Consente il cross-modal retrieval (query testuale -> asset visivo + codice generato).
    """
    def __init__(self, assets_dir="data/assets", metadata_file="data/assets/metadata.json"):
        self.assets_dir = assets_dir
        self.metadata_file = metadata_file
        self.assets = []
        self._load_or_generate_assets()

    def _load_or_generate_assets(self):
        """Carica gli asset indicizzati o genera quelli sintetici di default."""
        os.makedirs(self.assets_dir, exist_ok=True)

        # Se la cartella è vuota o manca il file dei metadati, generiamo gli asset sintetici
        if not os.path.exists(self.metadata_file) or len(os.listdir(self.assets_dir)) <= 1:
            print("[MultimodalRAG] Inizializzazione asset sintetici C64 di default...")
            self.assets = extract_and_save_all_synthetic(self.assets_dir)
            self.save_metadata()
        else:
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.assets = json.load(f)
                print(f"[MultimodalRAG] Caricati {len(self.assets)} asset grafici dall'indice.")
            except Exception as e:
                print(f"[MultimodalRAG] Errore caricamento metadati: {e}. Rigenerazione in corso...")
                self.assets = extract_and_save_all_synthetic(self.assets_dir)
                self.save_metadata()

    def save_metadata(self):
        """Salva l'indice dei metadati in un file JSON."""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.assets, f, indent=2, ensure_ascii=False)

    def register_asset(self, asset_id, name, asset_type, mode, dimensions, filepath, description):
        """Registra un nuovo asset grafico nel sistema."""
        asset = {
            "id": asset_id,
            "name": name,
            "type": asset_type,
            "mode": mode,
            "dimensions": dimensions,
            "filepath": filepath,
            "description": description
        }
        # Sostituisci se esiste già
        self.assets = [a for a in self.assets if a["id"] != asset_id]
        self.assets.append(asset)
        self.save_metadata()
        return asset

    def search_assets(self, query):
        """Effettua una ricerca testuale semplice nell'indice metadati degli asset."""
        if not query:
            return self.assets

        q = query.lower()
        results = []
        for asset in self.assets:
            if (q in asset["name"].lower() or
                q in asset["type"].lower() or
                q in asset["description"].lower() or
                q in asset["mode"].lower()):
                results.append(asset)
        return results

    def get_asset_by_id(self, asset_id):
        """Recupera un asset specifico tramite il suo ID."""
        for asset in self.assets:
            if asset["id"] == asset_id:
                return asset
        return None

    def get_basic_code_for_sprite(self, asset_id, address=12288):
        """Genera codice BASIC v2 per caricare e visualizzare lo sprite sul C64."""
        asset = self.get_asset_by_id(asset_id)
        if not asset or asset["type"] != "sprite":
            return ""

        # Calcolo blocco puntatore sprite (address / 64)
        pointer_val = address // 64
        # Per semplicità, leggiamo i byte del file se registrato o usiamo il generatore
        from utils.c64_graphics_extractor import generate_synthetic_sprite_data
        pattern = "balloon" if "balloon" in asset_id else "alien"
        data = generate_synthetic_sprite_data(pattern)

        # Generiamo righe di POKE BASIC
        lines = []
        lines.append(f"10 REM --- VISUALIZZA SPRITE {asset['name'].upper()} ---")
        lines.append(f"20 V = 53248: REM INDIRIZZO BASE VIC-II")
        lines.append(f"30 POKE V+21, 1: REM ABILITA SPRITE 0")
        lines.append(f"40 POKE V, 100: POKE V+1, 120: REM POSIZIONE X=100, Y=120")
        lines.append(f"50 POKE 2040, {pointer_val}: REM PUNTARELLO SPRITE 0 A ${address:04X}")
        lines.append(f"60 FOR I = 0 TO 62")
        lines.append(f"70 READ D: POKE {address}+I, D")
        lines.append(f"80 NEXT I")
        lines.append(f"90 POKE V+39, 1: REM COLORE SPRITE 0 (BIANCO/GIALLO)")

        if asset["mode"] == "multicolor":
            lines.append(f"100 POKE V+28, 1: REM ATTIVA MULTICOLOR SPRITE 0")
            lines.append(f"110 POKE V+37, 2: REM COLORE MULTICOLOR 1")
            lines.append(f"120 POKE V+38, 3: REM COLORE MULTICOLOR 2")

        lines.append(f"190 END")

        # Aggiungi le righe DATA (10 byte per riga per leggibilità)
        line_num = 200
        for i in range(0, len(data), 10):
            chunk = data[i:i+10]
            data_str = ",".join(str(b) for b in chunk)
            lines.append(f"{line_num} DATA {data_str}")
            line_num += 10

        return "\n".join(lines)

    def get_asm_code_for_sprite(self, asset_id, address=12288):
        """Genera codice Assembly 6502 compatibile con ACME per caricare lo sprite."""
        asset = self.get_asset_by_id(asset_id)
        if not asset or asset["type"] != "sprite":
            return ""

        pointer_val = address // 64
        from utils.c64_graphics_extractor import generate_synthetic_sprite_data
        pattern = "balloon" if "balloon" in asset_id else "alien"
        data = generate_synthetic_sprite_data(pattern)

        asm = []
        asm.append(f"; --- ASM PER SPRITE {asset['name'].upper()} ---")
        asm.append(f"* = $0801")
        asm.append(f"        !byte $0b, $08, $0a, $00, $9e, $32, $30, $36, $31, $00, $00, $00 ; SYS 2061")
        asm.append(f"")
        asm.append(f"init_sprite:")
        asm.append(f"        sei")
        asm.append(f"        lda #1")
        asm.append(f"        sta $d015        ; Abilita sprite 0")
        asm.append(f"        lda #100")
        asm.append(f"        sta $d000        ; Sprite 0 X")
        asm.append(f"        sta $d001        ; Sprite 0 Y")
        asm.append(f"        lda #{pointer_val}")
        asm.append(f"        sta $07f8        ; Imposta puntatore sprite 0")

        if asset["mode"] == "multicolor":
            asm.append(f"        lda #1")
            asm.append(f"        sta $d01c        ; Attiva multicolor sprite 0")
            asm.append(f"        lda #2")
            asm.append(f"        sta $d025        ; Colore multicolor 1")
            asm.append(f"        lda #3")
            asm.append(f"        sta $d026        ; Colore multicolor 2")

        asm.append(f"        lda #1")
        asm.append(f"        sta $d027        ; Colore primario sprite 0")

        # Copia dei dati dello sprite nella destinazione
        asm.append(f"")
        asm.append(f"        ; Copia dei dati dello sprite nella RAM a ${address:04X}")
        asm.append(f"        ldx #0")
        asm.append(f"copy_loop:")
        asm.append(f"        lda sprite_data, x")
        asm.append(f"        sta {address}, x")
        asm.append(f"        inx")
        asm.append(f"        cpx #63")
        asm.append(f"        bne copy_loop")
        asm.append(f"        cli")
        asm.append(f"        rts")
        asm.append(f"")

        # Dati dello sprite
        asm.append(f"sprite_data:")
        for i in range(0, len(data), 8):
            chunk = data[i:i+8]
            bytes_str = ", ".join(f"${b:02x}" for b in chunk)
            asm.append(f"        !byte {bytes_str}")

        return "\n".join(asm)

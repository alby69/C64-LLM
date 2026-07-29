import os
import gradio as gr
from agent.multimodal_rag import MultimodalRAG

class AssetGallery:
    """
    Rappresenta la galleria degli asset grafici C64 (sprite, character set, bitmap).
    Consente di visualizzare i file PNG generati, cercarli e generare codice di caricamento C64.
    """
    def __init__(self):
        self.rag = MultimodalRAG()

    def render_gallery_html(self, query=""):
        """Genera una griglia HTML degli asset corrispondenti alla ricerca."""
        assets = self.rag.search_assets(query)
        if not assets:
            return "<div style='color: #ff9900; font-weight: bold; padding: 20px; text-align: center;'>Nessun asset grafico trovato per la query specificata.</div>"

        cards = []
        for asset in assets:
            # Leggiamo il file come base64 per incorporarlo direttamente se necessario, o usiamo il percorso relativo
            # Gradio serve i file dal percorso assoluto o relativo se configurato, per semplicità usiamo il percorso web di Gradio o passiamo l'immagine direttamente.
            # Siccome Gradio permette di visualizzare i file locali usando percorsi locali se consentiti, oppure convertendo in base64:
            import base64
            img_b64 = ""
            if os.path.exists(asset["filepath"]):
                with open(asset["filepath"], "rb") as img_file:
                    img_b64 = base64.b64encode(img_file.read()).decode("utf-8")

            img_src = f"data:image/png;base64,{img_b64}" if img_b64 else ""

            card = f"""
            <div style="border: 2px solid #5a5ad6; border-radius: 6px; background-color: #1a1a2e; color: #fff; padding: 10px; width: 220px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="background-color: #000; padding: 15px; border-radius: 4px; display: flex; justify-content: center; align-items: center; height: 100px;">
                        <img src="{img_src}" style="image-rendering: pixelated; width: 64px; height: auto;" alt="{asset['name']}">
                    </div>
                    <h4 style="margin: 10px 0 4px 0; color: #00d2ff; font-size: 14px; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{asset['name']}</h4>
                    <span style="font-size: 11px; background-color: #3b3b98; padding: 2px 6px; border-radius: 3px; color: #a3e5ff;">{asset['type'].upper()} - {asset['mode'].upper()}</span>
                    <p style="font-size: 11px; color: #ccc; margin-top: 8px; line-height: 1.3; height: 50px; overflow-y: auto;">{asset['description']}</p>
                </div>
                <div style="margin-top: 10px; border-top: 1px solid #333; padding-top: 8px;">
                    <button onclick="window.parent.postMessage({{type: 'select_asset', id: '{asset['id']}'}}, '*')" style="width: 100%; background-color: #0088cc; border: none; color: white; padding: 4px 8px; font-size: 11px; font-weight: bold; cursor: pointer; border-radius: 3px;">SELEZIONA</button>
                </div>
            </div>
            """
            cards.append(card)

        return f"""
        <div style="display: flex; flex-wrap: wrap; gap: 15px; justify-content: center; padding: 10px 0;">
            {"".join(cards)}
        </div>
        """

    def generate_c64_code(self, asset_id, format_type="BASIC"):
        """Genera codice di visualizzazione per l'asset selezionato nel formato desiderato."""
        if format_type == "BASIC":
            return self.rag.get_basic_code_for_sprite(asset_id)
        else:
            return self.rag.get_asm_code_for_sprite(asset_id)

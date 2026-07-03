import re
import json
import logging
from pathlib import Path
import yaml
from internetarchive import search_items, get_item
from utils.prompt_manager import PromptManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebCrawlerAgent")

class WebCrawlerAgent:
    def __init__(self, model_backend=None, kb_path="data/kb", config_path="config/crawler_sources.yaml"):
        self.backend = model_backend
        self.pm = PromptManager()
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

        # Assicura che le cartelle di configurazione esistano
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Cartella temporanea per download
        self.tmp_path = Path("data/raw/.tmp")
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.sources = self._load_sources()
        self.status_file = self.config_path.parent / "crawler_status.json"

    def _load_sources(self):
        """Carica la lista delle fonti dal file YAML."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('sources', [])
        return []

    def _load_status(self):
        """Carica lo stato dell'ultimo crawling."""
        if self.status_file.exists():
            with open(self.status_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_status(self, status):
        """Salva lo stato del crawling."""
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)

    def check_updates(self):
        """Controlla quali fonti necessitano di un aggiornamento."""
        status = self._load_status()
        to_update = []
        for source in self.sources:
            last_checked = status.get(source['name'], {}).get('last_checked')
            # Per ora semplice: se non c'è nel log, va aggiornato
            if not last_checked:
                to_update.append(source)
        return to_update

    def search_archive_org(self, query="commodore 64 programming", limit=5):
        """Cerca libri e documenti su Archive.org."""
        logger.info(f"Searching Archive.org for: {query}")
        search = search_items(f'{query} AND mediatype:texts')
        results = []
        for i, result in enumerate(search):
            if i >= limit:
                break
            itemid = result['identifier']
            item = get_item(itemid)
            metadata = item.metadata
            results.append({
                "id": itemid,
                "title": metadata.get('title'),
                "author": metadata.get('creator'),
                "year": metadata.get('date'),
                "description": metadata.get('description'),
                "url": f"https://archive.org/details/{itemid}"
            })
        return results

    def download_archive_pdf(self, item_id, dest_path):
        """Scarica il PDF di un item da Archive.org."""
        item = get_item(item_id)
        pdf_file = next((f for f in item.files if f['name'].endswith('.pdf')), None)
        if pdf_file:
            logger.info(f"Downloading PDF: {pdf_file['name']}")
            dest_file = Path(dest_path) / pdf_file['name']
            item.download(files=[pdf_file['name']], destdir=dest_path, verbose=True)
            return dest_file
        return None

    def transform_to_obsidian(self, content, source_info):
        """Usa l'LLM per trasformare il testo grezzo in una nota Obsidian strutturata."""
        max_chars = 6000
        if len(content) > max_chars:
            logger.info(f"Content truncated from {len(content)} to {max_chars} chars.")
            content = content[:max_chars]

        if not self.backend:
            # Fallback a una trasformazione base se non c'è LLM
            return self._basic_transform(content, source_info)

        system_prompt = self.pm.get_prompt("crawler.transform.system")
        user_prompt = f"SOURCE INFO: {json.dumps(source_info)}\n\nCONTENT:\n{content}" # Già troncato

        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        transformed = self.backend.generate(prompt, max_new_tokens=1024, temperature=0.1)
        return transformed

    def _basic_transform(self, content, source_info):
        """Trasformazione base senza LLM."""
        title = source_info.get('title', 'Unknown Title')
        source_url = source_info.get('url', '')
        author = source_info.get('author', 'Unknown')

        header = f"---\ntitle: \"{title}\"\nauthor: \"{author}\"\nsource: \"{source_url}\"\ntags: [c64, research]\n---\n\n"
        return header + f"# {title}\n\n{content}"

    def save_note(self, content, category, filename):
        """Salva la nota nella struttura cartelle di Obsidian."""
        category_path = self.kb_path / category
        category_path.mkdir(parents=True, exist_ok=True)

        # Pulisci nome file
        clean_name = re.sub(r'[^\w\-_.]', '_', filename)
        if not clean_name.endswith(".md"):
            clean_name += ".md"

        file_path = category_path / clean_name
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"Saved Obsidian note: {file_path}")
        return file_path

if __name__ == "__main__":
    # Test rapido
    crawler = WebCrawlerAgent()
    results = crawler.search_archive_org(limit=2)
    for r in results:
        print(f"Found: {r['title']} ({r['url']})")

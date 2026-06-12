import re
import json
import logging
from pathlib import Path
from internetarchive import search_items, get_item
from utils.prompt_manager import PromptManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebCrawlerAgent")

class WebCrawlerAgent:
    def __init__(self, model_backend=None, kb_path="knowledge_base"):
        self.backend = model_backend
        self.pm = PromptManager()
        self.kb_path = Path(kb_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)

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

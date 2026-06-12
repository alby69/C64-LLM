import os
import logging
from pathlib import Path
from agent.crawler import WebCrawlerAgent
from pipeline.pdf2text import extract_text_pro

# Mock per il backend se non disponibile per test rapidi
class MockBackend:
    def generate(self, prompt, **kwargs):
        # Ritorna un markdown fake per test
        return "---\ntitle: \"Mock Note\"\ntags: [mock]\n---\n# Mock\nContenuto trasformato."

from datetime import datetime

def run_crawler_pipeline(query=None, limit=1):
    crawler = WebCrawlerAgent(model_backend=MockBackend())

    # 1. Monitoraggio Sorgenti
    sources_to_check = crawler.check_updates()
    logger.info(f"Found {len(sources_to_check)} sources to check from config.")

    # 2. Esecuzione (per ora Archive.org come esempio)
    # In futuro questa funzione chiamerà scraper diversi in base al 'type' della sorgente
    results = []
    if query:
        results = crawler.search_archive_org(query=query, limit=limit)

    for item in results:
        # 2. Download
        tmp_dir = Path("data/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = crawler.download_archive_pdf(item['id'], str(tmp_dir / item['id']))

        if pdf_path and pdf_path.exists():
            # 3. Extract Text
            text = extract_text_pro(str(pdf_path))

            # 4. Transform with LLM (or mock)
            obsidian_note = crawler.transform_to_obsidian(text, item)

            # 5. Save to Knowledge Base
            # Decidiamo la categoria in base al titolo o lasciamo all'LLM (qui mock)
            category = "Research"
            crawler.save_note(obsidian_note, category, item['title'])

            # Update status
            status = crawler._load_status()
            status[item.get('id', item['title'])] = {
                "last_checked": datetime.now().isoformat(),
                "source": item.get('url')
            }
            crawler._save_status(status)

            # Pulizia (opzionale, decommentare per liberare spazio)
            # import shutil
            # shutil.rmtree(pdf_path.parent)
        else:
            print(f"No PDF found for {item['title']}")

if __name__ == "__main__":
    run_crawler_pipeline("commodore 64 assembly programming", limit=1)

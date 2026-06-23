import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("run_crawler")
from agent.crawler import WebCrawlerAgent

class MockBackend:
    def generate(self, prompt, **kwargs):
        return "---\ntitle: \"Mock Note\"\ntags: [mock]\n---\n# Mock\nContenuto trasformato."

from datetime import datetime

def extract_with_marker(pdf_path):
    from pipeline.pdf2marker import convert_pdf
    result = convert_pdf(str(pdf_path), str(pdf_path).replace(".pdf", ""))
    if result["status"] == "ok":
        with open(result["text"], "r", encoding="utf-8") as f:
            return f.read()
    return ""

def run_crawler_pipeline(query=None, limit=1):
    crawler = WebCrawlerAgent(model_backend=MockBackend())

    sources_to_check = crawler.check_updates()
    logger.info(f"Found {len(sources_to_check)} sources to check from config.")

    results = []
    if query:
        results = crawler.search_archive_org(query=query, limit=limit)

    for item in results:
        tmp_dir = Path("data/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = crawler.download_archive_pdf(item['id'], str(tmp_dir / item['id']))

        if pdf_path and pdf_path.exists():
            text = extract_with_marker(pdf_path)

            obsidian_note = crawler.transform_to_obsidian(text, item)

            category = "Research"
            crawler.save_note(obsidian_note, category, item['title'])

            status = crawler._load_status()
            status[item.get('id', item['title'])] = {
                "last_checked": datetime.now().isoformat(),
                "source": item.get('url')
            }
            crawler._save_status(status)
        else:
            print(f"No PDF found for {item['title']}")

if __name__ == "__main__":
    run_crawler_pipeline("commodore 64 assembly programming", limit=1)

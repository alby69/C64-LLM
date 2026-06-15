import sys
from pathlib import Path
from pipeline.c64_asm_scraper import Downloader, Scraper

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline/scrape_url.py <url> [name]")
        sys.exit(1)

    url = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else "custom"

    site = {
        "name": name,
        "label": url,
        "start_urls": [url],
        "base": url,
        "follow_links": True,
        "max_depth": 2,
        "extract_code_blocks": True,
    }

    downloader = Downloader(Path("data/src"))
    scraper = Scraper(downloader, delay=1.5)
    scraper.run_site(site)
    print(f"\nScraping completato. File salvati: {downloader.total_saved}")

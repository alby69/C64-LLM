import os
import re
import sys
import time
import hashlib
import logging
import urllib3
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("scrape_docs")

import requests

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (compatible; C64DocScraper/1.0)"})

PDF_EXT = ".pdf"
TEXT_EXT = {".txt", ".html", ".htm"}
SKIP_EXT = {".d64", ".d81", ".gif", ".jpg", ".png", ".zip", ".tar", ".gz", ".mp3", ".sid"}

VISITED = set()
DOWNLOADED = set()


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:12]


def load_downloaded_hashes(dest):
    hashes = set()
    if os.path.exists(dest):
        for fname in os.listdir(dest):
            path = os.path.join(dest, fname)
            if os.path.isfile(path):
                hashes.add(file_hash(path))
    return hashes


def get_page(url, timeout=20):
    for verify in [False]:
        try:
            r = SESSION.get(url, timeout=timeout, verify=verify)
            r.raise_for_status()
            return r
        except Exception as e:
            log.warning(f"  ✗ {url}: {e}")
            return None


def is_dir_listing(html):
    return bool(re.search(r"<img[^>]*/icons/folder", html, re.I)) or bool(
        re.search(r"Parent Directory</a>", html, re.I)
    )


def extract_links(html, base_url):
    links = set()
    for m in re.finditer(r'href\s*=\s*"([^"]*)"', html, re.I):
        href = m.group(1)
        if href in ("", "/", "#"):
            continue
        if href.startswith("mailto:") or href.startswith("javascript"):
            continue
        absolute = urljoin(base_url, href)
        links.add(absolute)
    return links


def get_ext(url):
    path = urlparse(url).path.lower()
    _, ext = os.path.splitext(path)
    return ext


def download_pdf(url, dest, seen_hashes):
    ext = get_ext(url)
    if ext != PDF_EXT:
        return False
    try:
        r = SESSION.get(url, timeout=30, verify=False, stream=True)
        r.raise_for_status()
        fname = os.path.basename(urlparse(url).path)
        if not fname:
            fname = "unknown.pdf"
        fpath = os.path.join(dest, fname)
        with open(fpath, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        h = file_hash(fpath)
        if h in seen_hashes:
            os.remove(fpath)
            log.info(f"  ↷ Duplicato: {fname}")
            return False
        seen_hashes.add(h)
        sz = os.path.getsize(fpath)
        log.info(f"  ✔ {fname} ({sz // 1024}K)")
        return True
    except Exception as e:
        log.warning(f"  ✗ Download fallito {url}: {e}")
        return False


def crawl(start_url, dest, seen_hashes, depth=0, max_depth=3):
    if depth > max_depth or start_url in VISITED:
        return 0
    VISITED.add(start_url)

    ext = get_ext(start_url)
    if ext in SKIP_EXT:
        return 0

    if ext == PDF_EXT:
        return 1 if download_pdf(start_url, dest, seen_hashes) else 0

    log.info(f"{'  ' * depth}[{depth}] {start_url}")
    resp = get_page(start_url)
    if resp is None:
        return 0

    if "html" not in resp.headers.get("Content-Type", "") and "text" not in resp.headers.get("Content-Type", ""):
        return 0

    html = resp.text
    links = extract_links(html, start_url)
    is_dir = is_dir_listing(html)

    total = 0
    for link in sorted(links):
        link_ext = get_ext(link)
        if link_ext in SKIP_EXT:
            continue
        if link_ext == PDF_EXT:
            if download_pdf(link, dest, seen_hashes):
                total += 1
        elif is_dir or depth == 0:
            total += crawl(link, dest, seen_hashes, depth + 1, max_depth)

    return total


def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline/scrape_docs.py <url> [dest]")
        sys.exit(1)

    url = sys.argv[1].strip()
    base_dest = sys.argv[2] if len(sys.argv) > 2 else "data/input"

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").split(".")[0]
    path_part = parsed.path.strip("/").replace("/", "_") if parsed.path.strip("/") else ""
    subdir = f"{domain}_{path_part}" if path_part else domain
    subdir = re.sub(r'[^a-zA-Z0-9_-]', '_', subdir)[:60]
    dest = os.path.join(base_dest, subdir)
    os.makedirs(dest, exist_ok=True)

    log.info(f"Scarico PDF da: {url}")
    log.info(f"Destinazione: {dest}")
    log.info("")

    seen = load_downloaded_hashes(dest)
    total = crawl(url, dest, seen)
    log.info(f"\nTotale PDF scaricati: {total}")


if __name__ == "__main__":
    main()

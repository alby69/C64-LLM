#!/usr/bin/env python3
"""
C64 Assembly Scraper
====================
Scarica file assembly 6502/6510 per Commodore 64 da vari siti web.
I file vengono organizzati in sottocartelle per ogni sito sorgente.

Dipendenze:
    pip install requests beautifulsoup4 lxml

Uso:
    python c64_asm_scraper.py
    python c64_asm_scraper.py --output ./mia_cartella --delay 1.5
"""

import os
import re
import time
import argparse
import hashlib
import logging
import urllib3
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from typing import Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installa le dipendenze con:\n  pip install requests beautifulsoup4 lxml")
    exit(1)

# ─── Configurazione logging ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("c64_scraper")

# ─── Estensioni e pattern di interesse ───────────────────────────────────────

ASM_EXTENSIONS = {
    ".asm", ".s", ".a", ".src", ".inc",
    ".65s", ".6502", ".6510", ".prg",
}

PDF_EXTENSIONS = {".pdf"}

# Pattern nel nome file che suggeriscono codice assembly C64
ASM_FILENAME_PATTERNS = [
    r"\.asm$", r"\.s$", r"6502", r"6510", r"c64",
    r"commodore", r"_asm", r"-asm", r"\.a$",
]

# Parole chiave nel contenuto che confermano che è assembly 6502/6510
ASM_CONTENT_KEYWORDS = [
    # Load/Store
    "lda ", "ldx ", "ldy ", "sta ", "stx ", "sty ",
    "lda #", "lda $", "ldx #", "ldx $", "ldy #", "ldy $",
    "sta $", "stx $", "sty $",
    # Arithmetic
    "adc ", "sbc ", "adc #", "sbc #",
    # Logical
    "and ", "ora ", "eor ", "and #", "ora #", "eor #",
    # Shift/Rotate
    "asl ", "lsr ", "rol ", "ror ",
    # Increment/Decrement
    "inc ", "dec ", "inx ", "dex ", "iny ", "dey ",
    # Branch
    "beq ", "bne ", "bpl ", "bmi ", "bcc ", "bcs ", "bvc ", "bvs ",
    # Jump/Subroutine
    "jmp ", "jsr ", "rts ", "rti ", "brk ",
    # Compare
    "cmp ", "cpx ", "cpy ",
    # Bit test
    "bit ",
    # Flags
    "clc", "sec", "cli", "sei", "clv", "cld", "sed",
    # Stack/Transfer
    "pha ", "pla ", "php ", "plp ", "txs ", "tsx ",
    "tax ", "tay ", "txa ", "tya ",
    # NOP
    "nop ",
    # Pseudo/directives
    "*=$", ".org", ".byte", ".word", ".text", ".ascii",
    # C64 specific
    "; c64", "; commodore", "; 6502", "; 6510",
    "kernal", "sid ", "vic ", "$d020", "$d800", "$0400",
    "processor 6502", "processor 6510",
]

# ─── Siti target ─────────────────────────────────────────────────────────────

TARGETS = [
    # ── 6502.org: enorme archivio di codice 6502 ──────────────────────────
    {
        "name": "6502org",
        "label": "6502.org",
        "start_urls": [
            "http://www.6502.org/source/",
            "http://www.6502.org/tutorials/",
            "http://www.6502.org/mini-projects/",
        ],
        "base": "http://www.6502.org",
        "follow_links": True,
        "max_depth": 3,
    },
    # ── codebase64.org: wiki dedicato al C64 ──────────────────────────────
    {
        "name": "codebase64",
        "label": "Codebase64",
        "start_urls": [
            "https://codebase64.org/doku.php?id=base:6502_6510_coding",
            "https://codebase64.org/doku.php?id=base:start",
            "https://codebase64.org/doku.php?id=base:loops",
            "https://codebase64.org/doku.php?id=base:sorting",
            "https://codebase64.org/doku.php?id=base:math",
            "https://codebase64.org/doku.php?id=base:multiplexer",
            "https://codebase64.org/doku.php?id=base:sprite_multiplexer",
            "https://codebase64.org/doku.php?id=base:sid",
        ],
        "base": "https://codebase64.org",
        "follow_links": True,
        "max_depth": 2,
        "extract_code_blocks": True,   # estrae blocchi <code>/<pre> come .asm
    },
    # ── c64-wiki.com ──────────────────────────────────────────────────────
    {
        "name": "c64wiki",
        "label": "C64-Wiki",
        "start_urls": [
            "https://www.c64-wiki.com/wiki/Machine_Language",
            "https://www.c64-wiki.com/wiki/Assembly",
            "https://www.c64-wiki.com/wiki/6510",
            "https://www.c64-wiki.com/wiki/Assembler",
        ],
        "base": "https://www.c64-wiki.com",
        "follow_links": False,
        "extract_code_blocks": True,
    },
    # ── codebase64 file diretti ────────────────────────────────────────────
    {
        "name": "codebase64_files",
        "label": "Codebase64 Files",
        "start_urls": [
            "https://codebase64.org/doku.php?id=base:index",
        ],
        "base": "https://codebase64.org",
        "follow_links": True,
        "max_depth": 2,
        "extract_code_blocks": True,
    },
    # ── GitHub: repository pubblici con tag c64 / 6502 ────────────────────
    {
        "name": "github_c64",
        "label": "GitHub C64",
        "start_urls": [
            "https://github.com/topics/commodore-64",
            "https://github.com/topics/6502",
            "https://github.com/topics/c64",
        ],
        "base": "https://github.com",
        "follow_links": True,
        "max_depth": 3,
        "github_mode": True,   # logica speciale per GitHub raw
    },
    # ── The Fridge (classici sorgenti C64) ────────────────────────────────
    {
        "name": "thefridge",
        "label": "The Fridge",
        "start_urls": [
            "http://www.ffd2.com/fridge/programs/",
            "http://www.ffd2.com/fridge/chessmate/",
        ],
        "base": "http://www.ffd2.com",
        "follow_links": True,
        "max_depth": 3,
    },
    # ── Lemon64 code section ──────────────────────────────────────────────
    {
        "name": "lemon64",
        "label": "Lemon64",
        "start_urls": [
            "https://www.lemon64.com/forum/viewforum.php?f=8",
        ],
        "base": "https://www.lemon64.com",
        "follow_links": False,
        "extract_code_blocks": True,
    },
    # ── Project: 64 source archive ────────────────────────────────────────
    {
        "name": "project64",
        "label": "Project 64",
        "start_urls": [
            "https://project64.c64.org/hw.htm",
            "https://project64.c64.org/pr.htm",
        ],
        "base": "https://project64.c64.org",
        "follow_links": True,
        "max_depth": 2,
    },
    # ── NES Dev wiki (utile anche per 6502 generico) ──────────────────────
    {
        "name": "nesdev",
        "label": "NESdev 6502",
        "start_urls": [
            "https://www.nesdev.org/wiki/6502_assembly_optimisations",
            "https://www.nesdev.org/wiki/6502_instructions",
        ],
        "base": "https://www.nesdev.org",
        "follow_links": False,
        "extract_code_blocks": True,
    },
]

# ─── Sessione HTTP ────────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (compatible; C64AsmScraper/1.0; "
        "+https://github.com/c64-asm-scraper)"
    ),
    "Accept-Language": "en-US,en;q=0.9",
})

# ─── Utilità ──────────────────────────────────────────────────────────────────

def safe_filename(name: str) -> str:
    """Rimuove caratteri non validi dal nome file."""
    name = unquote(name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name[:200].strip("._")


def file_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()[:8]


def looks_like_asm(content: str) -> bool:
    """Controlla se il testo sembra assembly 6502/6510."""
    lower = content.lower()
    hits = sum(1 for kw in ASM_CONTENT_KEYWORDS if kw.lower() in lower)
    return hits >= 3


def get_page(url: str, timeout: int = 15) -> Optional[requests.Response]:
    for attempt, verify in enumerate([True, False]):
        try:
            r = SESSION.get(url, timeout=timeout, allow_redirects=True, verify=verify)
            r.raise_for_status()
            return r
        except Exception as exc:
            if attempt == 1 or "SSL" not in str(exc):
                log.warning(f"  ✗ Impossibile scaricare {url}: {exc}")
                return None
            log.info(f"  ↻ Riprovo senza verifica SSL: {url}")
    return None


# ─── Salvataggio file ─────────────────────────────────────────────────────────

class Downloader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._seen_hashes: set = set()
        self.total_saved = 0
        self._load_existing_files()

    def _load_existing_files(self):
        """Carica i file esistenti per evitare duplicati."""
        dirs_to_check = [self.base_dir, self.base_dir.parent / "input"]
        for base in dirs_to_check:
            if not base.exists():
                continue
            for site_dir in base.iterdir():
                if site_dir.is_dir():
                    for f in site_dir.iterdir():
                        if f.is_file():
                            try:
                                h = file_hash(f.read_bytes())
                                self._seen_hashes.add(h)
                            except Exception:
                                pass

    def save(self, site_name: str, filename: str, content: bytes, is_pdf: bool = False) -> bool:
        """Salva un file nella sottocartella del sito; evita duplicati."""
        h = file_hash(content)
        if h in self._seen_hashes:
            log.debug(f"  ↷ Duplicato saltato: {filename}")
            return False
        self._seen_hashes.add(h)

        if is_pdf:
            dest_dir = self.base_dir.parent / "input" / safe_filename(site_name)
        else:
            dest_dir = self.base_dir / safe_filename(site_name)
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest = dest_dir / safe_filename(filename)
        # evita collisioni di nome
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            dest = dest_dir / f"{stem}_{h}{suffix}"

        dest.write_bytes(content)
        self.total_saved += 1
        log.info(f"  ✔ Salvato: {dest}")
        return True

    def save_text(self, site_name: str, filename: str, text: str) -> bool:
        return self.save(site_name, filename, text.encode("utf-8", errors="replace"))


# ─── Scraper generico ─────────────────────────────────────────────────────────

class Scraper:
    def __init__(self, downloader: Downloader, delay: float = 1.0):
        self.dl = downloader
        self.delay = delay
        self._visited: set = set()

    # ── helpers ──────────────────────────────────────────────────────────

    def _wait(self):
        time.sleep(self.delay)

    def _is_asm_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in ASM_EXTENSIONS)

    def _is_asm_filename(self, name: str) -> bool:
        return any(re.search(p, name, re.I) for p in ASM_FILENAME_PATTERNS)

    def _extract_filename(self, url: str, fallback: str = "code") -> str:
        path = urlparse(url).path
        name = os.path.basename(path) or fallback
        if not any(name.lower().endswith(ext) for ext in ASM_EXTENSIONS):
            name += ".asm"
        return name

    # ── scarica un singolo file binario/testo ─────────────────────────────

    def download_file(self, url: str, site: dict) -> bool:
        if url in self._visited:
            return False
        self._visited.add(url)
        self._wait()
        log.info(f"  ↓ File: {url}")
        resp = get_page(url)
        if resp is None:
            return False
        content = resp.content
        filename = self._extract_filename(url)
        path_lower = urlparse(url).path.lower()
        is_pdf = any(path_lower.endswith(ext) for ext in PDF_EXTENSIONS)
        return self.dl.save(site["name"], filename, content, is_pdf=is_pdf)

    # ── estrae blocchi <code>/<pre> da una pagina HTML ────────────────────

    def extract_code_blocks(self, soup: BeautifulSoup, page_url: str, site: dict):
        blocks = soup.find_all(["pre", "code"])
        saved = 0
        for i, block in enumerate(blocks, 1):
            text = block.get_text()
            if len(text) < 20:
                continue
            if not looks_like_asm(text):
                continue
            # crea nome file dal titolo della pagina + indice
            title = soup.find("title")
            page_title = title.get_text(strip=True) if title else "page"
            page_title = re.sub(r"\s+", "_", page_title)[:60]
            filename = f"{page_title}_block{i:02d}.asm"
            if self.dl.save_text(site["name"], filename, text):
                saved += 1
        if saved:
            log.info(f"    → Estratti {saved} blocchi asm da {page_url}")

    # ── raccoglie link da una pagina ──────────────────────────────────────

    def collect_links(self, soup: BeautifulSoup, base_url: str, site: dict) -> list:
        links = []
        site_base = site["base"]
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            absolute = urljoin(base_url, href)
            # rimane nello stesso dominio
            if not absolute.startswith(site_base):
                continue
            if absolute in self._visited:
                continue
            links.append(absolute)
        return links

    # ── crawl ricorsivo di un sito ────────────────────────────────────────

    def crawl(self, url: str, site: dict, depth: int = 0):
        max_depth = site.get("max_depth", 2)
        if depth > max_depth or url in self._visited:
            return
        self._visited.add(url)

        # file diretto?
        if self._is_asm_url(url):
            self.download_file(url, site)
            return

        self._wait()
        log.info(f"  → Pagina (depth={depth}): {url}")
        resp = get_page(url)
        if resp is None:
            return

        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            # potrebbe essere un file binario
            if self._is_asm_filename(os.path.basename(urlparse(url).path)):
                filename = self._extract_filename(url)
                self.dl.save(site["name"], filename, resp.content)
            return

        soup = BeautifulSoup(resp.text, "lxml")

        # estrai blocchi di codice dalla pagina?
        if site.get("extract_code_blocks"):
            self.extract_code_blocks(soup, url, site)

        if not site.get("follow_links"):
            return

        links = self.collect_links(soup, url, site)
        for link in links:
            # file asm diretto → scarica subito
            if self._is_asm_url(link) or self._is_asm_filename(
                os.path.basename(urlparse(link).path)
            ):
                self.download_file(link, site)
            else:
                self.crawl(link, site, depth + 1)

    # ── logica speciale per GitHub ────────────────────────────────────────

    def crawl_github(self, url: str, site: dict, depth: int = 0):
        max_depth = site.get("max_depth", 3)
        if depth > max_depth or url in self._visited:
            return
        self._visited.add(url)

        self._wait()
        log.info(f"  → GitHub (depth={depth}): {url}")
        resp = get_page(url)
        if resp is None:
            return

        soup = BeautifulSoup(resp.text, "lxml")

        # pagina topic → link ai repository
        repo_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # link a repo es. /user/repo
            if re.match(r"^/[^/]+/[^/]+$", href) and "/topics/" not in href:
                full = "https://github.com" + href
                if full not in self._visited:
                    repo_links.append(full)

        for repo_url in repo_links[:20]:   # limita per non esagerare
            self._github_explore_repo(repo_url, site)

    def _github_explore_repo(self, repo_url: str, site: dict):
        """Naviga un repository GitHub cercando file .asm."""
        if repo_url in self._visited:
            return
        self._visited.add(repo_url)
        self._wait()
        log.info(f"  → Repo: {repo_url}")
        resp = get_page(repo_url)
        if resp is None:
            return

        soup = BeautifulSoup(resp.text, "lxml")
        # cerca link a file/directory nel repo
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # file .asm nel repository
            if re.search(r"\.(asm|s|6502|6510)$", href, re.I):
                # converti in raw URL
                raw = re.sub(
                    r"https://github\.com/([^/]+)/([^/]+)/blob/(.*)",
                    r"https://raw.githubusercontent.com/\1/\2/\3",
                    "https://github.com" + href if href.startswith("/") else href,
                )
                self.download_file(raw, site)
            # directory → esplora (1 livello solo)
            elif re.match(r"^/[^/]+/[^/]+/tree/", href):
                sub_url = "https://github.com" + href
                if sub_url not in self._visited:
                    self._visited.add(sub_url)
                    self._wait()
                    sub_resp = get_page(sub_url)
                    if sub_resp:
                        sub_soup = BeautifulSoup(sub_resp.text, "lxml")
                        for b in sub_soup.find_all("a", href=True):
                            bh = b["href"]
                            if re.search(r"\.(asm|s|6502|6510)$", bh, re.I):
                                raw = re.sub(
                                    r"/([^/]+)/([^/]+)/blob/(.*)",
                                    r"https://raw.githubusercontent.com/\1/\2/\3",
                                    bh,
                                )
                                if raw.startswith("/"):
                                    raw = "https://github.com" + bh
                                self.download_file(raw, site)

    # ── entry point per un singolo sito ──────────────────────────────────

    def run_site(self, site: dict):
        label = site.get("label", site["name"])
        log.info(f"\n{'='*60}")
        log.info(f"  Sito: {label}")
        log.info(f"{'='*60}")
        for url in site["start_urls"]:
            if site.get("github_mode"):
                self.crawl_github(url, site)
            else:
                self.crawl(url, site)


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Scarica file assembly 6502/6510 per Commodore 64 dal web."
    )
    p.add_argument(
        "--output", "-o",
        default="./data/src",
        help="Cartella di output (default: ./data/src)",
    )
    p.add_argument(
        "--delay", "-d",
        type=float,
        default=1.2,
        help="Secondi di pausa tra le richieste HTTP (default: 1.2)",
    )
    p.add_argument(
        "--sites", "-s",
        nargs="*",
        help="Nomi dei siti da scrapare (default: tutti). Es: --sites 6502org codebase64",
    )
    p.add_argument(
        "--list-sites",
        action="store_true",
        help="Elenca i siti disponibili ed esci",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.list_sites:
        print("\nSiti disponibili:")
        for t in TARGETS:
            print(f"  {t['name']:20s}  {t.get('label', '')}")
        return

    base_dir = Path(args.output)
    base_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Cartella output: {base_dir.resolve()}")

    downloader = Downloader(base_dir)
    scraper = Scraper(downloader, delay=args.delay)

    targets = TARGETS
    if args.sites:
        targets = [t for t in TARGETS if t["name"] in args.sites]
        if not targets:
            log.error(f"Nessun sito trovato per: {args.sites}")
            return

    for site in targets:
        try:
            scraper.run_site(site)
        except KeyboardInterrupt:
            log.info("\nInterrotto dall'utente.")
            break
        except Exception as exc:
            log.error(f"Errore nel sito {site['name']}: {exc}", exc_info=True)

    log.info(f"\n{'='*60}")
    log.info(f"  Completato! File scaricati: {downloader.total_saved}")
    log.info(f"  Cartella: {base_dir.resolve()}")
    log.info(f"{'='*60}")

    # Riepilogo per sito
    print("\nRiepilogo per sito (data/src/):")
    for d in sorted(base_dir.iterdir()):
        if d.is_dir():
            n = len(list(d.glob("*")))
            print(f"  {d.name:30s}  {n} file")

    input_dir = base_dir.parent / "input"
    if input_dir.exists():
        print("\nRiepilogo per sito (data/input/):")
        for d in sorted(input_dir.iterdir()):
            if d.is_dir():
                n = len(list(d.glob("*")))
                print(f"  {d.name:30s}  {n} file")


if __name__ == "__main__":
    main()

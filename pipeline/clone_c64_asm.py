#!/usr/bin/env python3
"""
C64 Assembly Dataset Builder
============================
Clona repo GitHub / Estrae file ASM / Crea dataset

Dipendenze:
    pip install requests beautifulsoup4

Uso:
    python clone_c64_asm.py
    python clone_c64_asm.py --output ./mia_cartella
"""

import os
import re
import sys
import time
import shutil
import hashlib
import logging
import argparse
import subprocess
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Installa le dipendenze con:\n  pip install requests beautifulsoup4")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("c64_clone")

REPO_LIST = [
    ("digitsensitive_c64", "https://github.com/digitsensitive/c64"),
    ("ktuukkan_c64-asm", "https://github.com/ktuukkan/c64-asm"),
    ("dani-Tb_c64-asm-samples", "https://github.com/dani-Tb/c64-asm-samples"),
    ("nealvis_c64_samples_kick", "https://github.com/nealvis/c64_samples_kick"),
    ("nealvis_nv_c64_util", "https://github.com/nealvis/nv_c64_util"),
    ("kindjie_6502Assembly", "https://github.com/kindjie/6502Assembly"),
    ("yackx_c64", "https://github.com/yackx/c64"),
    ("bryancandi_Commodore", "https://github.com/bryancandi/Commodore"),
    ("benmcevoy_c64", "https://github.com/benmcevoy/c64"),
    ("JohanSmet_c64_experiments", "https://github.com/JohanSmet/c64_experiments"),
    ("petriw_Commodore64Programming", "https://github.com/petriw/Commodore64Programming"),
    ("spiroharvey_c64", "https://github.com/spiroharvey/c64"),
    ("jyoberle_c64asm", "https://github.com/jyoberle/c64asm"),
    ("mwenge_iridisalpha", "https://github.com/mwenge/iridisalpha"),
    ("mwenge_gridrunner", "https://github.com/mwenge/gridrunner"),
    ("mwenge_matrix", "https://github.com/mwenge/matrix"),
    ("mwenge_attack-of-the-mutant-camels", "https://github.com/mwenge/attack-of-the-mutant-camels"),
    ("mwenge_batalyx", "https://github.com/mwenge/batalyx"),
    ("mwenge_metagalactic-llamas", "https://github.com/mwenge/metagalactic-llamas"),
    ("Piddewitt_C64-Game-Source-Code", "https://github.com/Piddewitt/C64-Game-Source-Code"),
    ("mist64_cbmsrc", "https://github.com/mist64/cbmsrc"),
    ("barryw_c64lib", "https://github.com/barryw/c64lib"),
    ("martinpiper_ACME", "https://github.com/martinpiper/ACME"),
    ("c64lib_common", "https://github.com/c64lib/common"),
    ("c64lib_chipset", "https://github.com/c64lib/chipset"),
    ("c64lib_text", "https://github.com/c64lib/text"),
    ("c64lib_copper64", "https://github.com/c64lib/copper64"),
    ("maciejmalecki_trex64", "https://github.com/maciejmalecki/trex64"),
    ("maciejmalecki_tony-demo", "https://github.com/maciejmalecki/tony-demo"),
    ("maciejmalecki_bluevessel", "https://github.com/maciejmalecki/bluevessel"),
    ("smnjameson_c64", "https://github.com/smnjameson/c64"),
    ("cliffordcarnmo_c64", "https://github.com/cliffordcarnmo/c64"),
    ("mrohmer_c64-assembly", "https://github.com/mrohmer/c64-assembly"),
    ("lhz_c64", "https://github.com/lhz/c64"),
    ("jblang_c64", "https://github.com/jblang/c64"),
    ("bitshifters_c64-fun", "https://github.com/bitshifters/c64-fun"),
    ("EngineersNeedArt_c64", "https://github.com/EngineersNeedArt/c64"),
]

ASM_EXTENSIONS = {".asm", ".a", ".s", ".inc", ".acme", ".kick", ".ka", ".src", ".lst"}


def check_deps():
    """Verifica che i comandi necessari siano disponibili."""
    for cmd in ["git", "find", "cp"]:
        if shutil.which(cmd) is None:
            log.error(f"Dipendenza mancante: {cmd}")
            sys.exit(1)


def clone_repo(name: str, url: str, base_dir: Path) -> bool:
    """Clona o aggiorna un repository direttamente in data/src/[name]."""
    dest = base_dir / name
    
    if (dest / ".git").exists():
        log.info(f"  [SKIP] {name} - gia' clonato, aggiorno...")
        try:
            subprocess.run(["git", "pull", "--quiet"], cwd=dest, capture_output=True, timeout=60)
            return True
        except Exception:
            return False
    
    log.info(f"  [CLONE] {name}")
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "--quiet", url, str(dest)],
            capture_output=True, timeout=300, check=True
        )
        log.info(f"  [OK] {name}")
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"  [FAIL] {name} - clone fallito: {e}")
        return False
    except subprocess.TimeoutExpired:
        log.error(f"  [FAIL] {name} - timeout")
        return False


def extract_asm_files(repo_name: str, src_dir: Path, dst_dir: Path) -> int:
    """Estrae i file ASM da un repository clonato."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    seen_hashes = set()
    
    for ext in ASM_EXTENSIONS:
        for filepath in src_dir.rglob(f"*{ext}"):
            if ".git" in filepath.parts or "node_modules" in filepath.parts:
                continue
            
            try:
                content = filepath.read_bytes()
                h = hashlib.md5(content).hexdigest()[:8]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
            except Exception:
                continue
            
            filename = filepath.name
            dest_file = dst_dir / filename
            
            if dest_file.exists():
                stem = dest_file.stem
                suffix = dest_file.suffix
                counter = 1
                while dst_dir.exists():
                    test_file = dst_dir / f"{stem}_{counter}{suffix}"
                    if not test_file.exists():
                        dest_file = test_file
                        break
                    counter += 1
            
            try:
                shutil.copy2(filepath, dest_file)
                count += 1
            except Exception as e:
                log.warning(f"    Errore copiando {filename}: {e}")
    
    log.info(f"  [FILES] {count} file ASM estratti -> {repo_name}/")
    return count


def download_codebase64(base_dir: Path) -> bool:
    """Scarica e estrae l'archivio HTML di Codebase64."""
    cb64_dir = base_dir / "codebase64_html_archive"
    cb64_dir.mkdir(parents=True, exist_ok=True)
    cb64_zip = cb64_dir / "codebase64_latest.zip"
    
    cb64_url = "https://codebase64.net/codebase64_latest.zip"
    
    log.info("  [DL] Codebase64 HTML Archive...")
    
    last_pct = -1
    try:
        response = requests.get(cb64_url, stream=True, timeout=120)
        response.raise_for_status()
        
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        
        with open(cb64_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        if pct - last_pct >= 5:
                            log.info(f"    Progresso: {pct:.1f}%")
                            last_pct = pct
        
        log.info("  [OK] Download completato")
        
        if shutil.which("unzip"):
            log.info("  [ZIP] Estrazione...")
            subprocess.run(
                ["unzip", "-q", str(cb64_zip), "-d", str(cb64_dir)],
                capture_output=True, check=True, timeout=120
            )
            log.info("  [OK] ZIP estratto")
            return True
        else:
            log.warning("  [WARN] unzip non disponibile")
            return False
            
    except Exception as e:
        log.error(f"  [FAIL] Download fallito: {e}")
        return False


def write_readme(base_dir: Path, total_repos: int, ok_repos: int, fail_repos: int, total_files: int):
    """Genera il README.md con le statistiche."""
    cb64_url = "https://codebase64.net/codebase64_latest.zip"
    
    readme = f"""# C64 Assembly Dataset

Generato il: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Repository inclusi ({total_repos})

| # | Cartella | URL |
|---|---|---|
"""
    for i, (name, url) in enumerate(REPO_LIST, 1):
        readme += f"| {i} | `{name}` | {url} |\n"
    readme += f"| - | `codebase64_html_archive` | {cb64_url} |\n"
    
    readme += f"""
## Estensioni raccolte
`.asm` `.a` `.s` `.inc` `.acme` `.kick` `.ka` `.src` `.lst`

## Statistiche
- Repository OK   : {ok_repos} / {total_repos}
- Repository FAIL : {fail_repos} / {total_repos}
- File ASM totali : {total_files}
"""
    
    (base_dir / "README.md").write_text(readme)
    log.info("README.md generato")


def main():
    parser = argparse.ArgumentParser(description="Clona repo GitHub / Estrae file ASM / Crea dataset")
    parser.add_argument("--output", "-o", default="./data/src", help="Cartella di output")
    parser.add_argument("--delay", "-d", type=float, default=1.0, help="Ritardo tra clone (secondi)")
    args = parser.parse_args()
    
    base_dir = Path(args.output)
    
    base_dir.mkdir(parents=True, exist_ok=True)
    
    log.info("========================================================")
    log.info("        C64 Assembly Dataset Builder  v1.0 (Python)")
    log.info("    Clona repo / Estrae file ASM / Crea dataset")
    log.info("========================================================")
    
    check_deps()
    
    log.info(f"Dataset directory : {base_dir}")
    log.info(f"Inizio            : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_repos = len(REPO_LIST)
    ok_repos = 0
    fail_repos = 0
    total_files = 0
    
    for i, (repo_name, repo_url) in enumerate(REPO_LIST, 1):
        log.info(f"\n--- [{i}/{total_repos}] {repo_name} ---")
        
        if clone_repo(repo_name, repo_url, base_dir):
            repo_dir = base_dir / repo_name
            count = sum(1 for f in repo_dir.rglob("*") if f.is_file() and ".git" not in f.parts)
            log.info(f"  [FILES] {count} file nel repo -> {repo_name}/")
            total_files += count
            ok_repos += 1
        else:
            fail_repos += 1
        
        time.sleep(args.delay)
    
    log.info("\n--- Codebase64 HTML Archive ---")
    download_codebase64(base_dir)
    
    write_readme(base_dir, total_repos, ok_repos, fail_repos, total_files)
    
    log.info(f"Fine: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 50)
    print("                  RIEPILOGO FINALE")
    print("=" * 50)
    print(f"\n  Repository totali       : {total_repos}")
    print(f"  Clonati con successo    : {ok_repos}")
    print(f"  Falliti                 : {fail_repos}")
    print(f"  File ASM totali         : {total_files}")
    print(f"  Dataset in              : {base_dir}")
    print("\nProssimi passi:")
    print(f"  File ASM estratti : {base_dir}/<nome_repo>/")


if __name__ == "__main__":
    main()
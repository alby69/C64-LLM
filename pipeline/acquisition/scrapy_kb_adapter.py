import os
import shutil
import hashlib
import logging
import subprocess
from pathlib import Path
import yaml
import frontmatter

logger = logging.getLogger("ScrapyKBAdapter")
logging.basicConfig(level=logging.INFO)

class ScrapyKBAdapter:
    """
    Adapter class to bridge C64-Scrapy, C64-KB-Agent and C64-LLM.
    Ensures seamless ingestion of scraped web pages, tutorials, and books.
    """

    def __init__(self, kb_agent_path="../C64-KB-Agent", scrapy_path="../C64-Scrapy", dest_kb_path="data/kb/scraped"):
        self.kb_agent_path = Path(kb_agent_path)
        self.scrapy_path = Path(scrapy_path)
        self.dest_kb_path = Path(dest_kb_path)

        # Ensure destination path exists
        self.dest_kb_path.mkdir(parents=True, exist_ok=True)
        self.hashes_file = self.dest_kb_path / ".synced_hashes.yaml"
        self.synced_hashes = self._load_hashes()

    def _load_hashes(self):
        """Loads MD5 hashes of previously synced documents."""
        if self.hashes_file.exists():
            try:
                with open(self.hashes_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Error loading synced hashes: {e}")
        return {}

    def _save_hashes(self):
        """Saves MD5 hashes to avoid unnecessary re-indexing."""
        try:
            with open(self.hashes_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.synced_hashes, f)
        except Exception as e:
            logger.error(f"Error saving synced hashes: {e}")

    def _get_md5(self, filepath):
        """Calculates MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def sync(self):
        """
        Syncs markdown files from C64-KB-Agent repository into C64-LLM target folder.
        Validates frontmatter and metadata during migration.
        """
        logger.info(f"Syncing knowledge from C64-KB-Agent: {self.kb_agent_path}")

        if not self.kb_agent_path.exists():
            logger.warning(f"C64-KB-Agent path '{self.kb_agent_path}' does not exist. Skipping sync.")
            return {"status": "error", "message": "KB-Agent path not found", "synced": 0}

        # Search for markdown files in C64-KB-Agent's scraped directory (e.g., 'scraped' or 'data/scraped')
        search_dirs = [
            self.kb_agent_path / "data/scraped",
            self.kb_agent_path / "scraped",
            self.kb_agent_path
        ]

        scraped_files = []
        for s_dir in search_dirs:
            if s_dir.exists():
                logger.info(f"Scanning directory: {s_dir}")
                scraped_files.extend(list(s_dir.glob("**/*.md")))
                # Break on first match to avoid duplicates if nested
                if len(scraped_files) > 0:
                    break

        if not scraped_files:
            logger.warning("No markdown files found in C64-KB-Agent directories.")
            return {"status": "ok", "message": "No files found", "synced": 0}

        synced_count = 0
        updated_count = 0
        ignored_count = 0

        for src_file in scraped_files:
            if src_file.name == "README.md":
                continue  # Skip root documentation

            file_md5 = self._get_md5(src_file)
            rel_name = src_file.name

            # Check if already synced and unchanged
            if rel_name in self.synced_hashes and self.synced_hashes[rel_name] == file_md5:
                ignored_count += 1
                continue

            # Load and validate frontmatter using standard YAML parser
            try:
                with open(src_file, 'r', encoding='utf-8', errors='replace') as f:
                    post = frontmatter.load(f)

                # Enforce minimal metadata schema (title and tags)
                metadata = post.metadata
                if not metadata.get("title"):
                    metadata["title"] = src_file.stem.replace("_", " ").title()
                if "tags" not in metadata:
                    metadata["tags"] = ["c64", "scraped"]
                elif isinstance(metadata["tags"], str):
                    metadata["tags"] = [metadata["tags"]]

                # Write formatted file with validated frontmatter
                dest_file = self.dest_kb_path / rel_name
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))

                is_update = rel_name in self.synced_hashes
                self.synced_hashes[rel_name] = file_md5
                synced_count += 1
                if is_update:
                    updated_count += 1

                logger.info(f"Ingested: {rel_name} (Tags: {metadata['tags']})")
            except Exception as e:
                logger.error(f"Failed to process {src_file.name}: {e}")

        self._save_hashes()
        logger.info(f"Sync complete. Ingested/Updated: {synced_count} (New: {synced_count-updated_count}, Updated: {updated_count}), Unchanged: {ignored_count}")
        return {
            "status": "ok",
            "synced": synced_count,
            "new": synced_count - updated_count,
            "updated": updated_count,
            "unchanged": ignored_count
        }

    def run_scrapy_spider(self, spider_name):
        """
        Triggers a specific spider inside the C64-Scrapy repository.
        Then triggers a sync to pull newly generated files.
        """
        if not self.scrapy_path.exists():
            logger.error(f"C64-Scrapy repository path '{self.scrapy_path}' not found.")
            return {"status": "error", "message": "C64-Scrapy path not found"}

        logger.info(f"Running spider '{spider_name}' in {self.scrapy_path}")
        try:
            # Running scrapy crawl <spider_name>
            # C64-Scrapy is configured to output into C64-KB-Agent's ingestion path
            result = subprocess.run(
                ["scrapy", "crawl", spider_name],
                cwd=self.scrapy_path,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Spider execution output: {result.stdout}")

            # Auto sync after spider run
            sync_res = self.sync()
            return {
                "status": "ok",
                "spider_stdout": result.stdout,
                "sync_result": sync_res
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running spider {spider_name}: {e.stderr}")
            return {"status": "error", "message": "Spider run failed", "details": e.stderr}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Test adapter locally (creates dummy folders if needed for dry run)
    adapter = ScrapyKBAdapter()
    print("Sync output:", adapter.sync())

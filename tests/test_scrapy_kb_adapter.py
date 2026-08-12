import os
import unittest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
import frontmatter

from pipeline.acquisition.scrapy_kb_adapter import ScrapyKBAdapter

class TestScrapyKBAdapter(unittest.TestCase):
    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.kb_agent_dir = self.temp_path / "C64-KB-Agent"
        self.scrapy_dir = self.temp_path / "C64-Scrapy"
        self.dest_kb_dir = self.temp_path / "dest_kb"

        self.kb_agent_dir.mkdir()
        self.scrapy_dir.mkdir()
        self.dest_kb_dir.mkdir()

        # Set up a mock scraped dir inside KB Agent
        self.kb_scraped_dir = self.kb_agent_dir / "data/scraped"
        self.kb_scraped_dir.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_adapter_init_defaults(self):
        # Test default path fallback mechanism
        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )
        self.assertEqual(adapter.kb_agent_path, self.kb_agent_dir)
        self.assertEqual(adapter.scrapy_path, self.scrapy_dir)
        self.assertEqual(adapter.dest_kb_path, self.dest_kb_dir)

    def test_sync_no_files_found(self):
        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )
        res = adapter.sync()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["synced"], 0)

    def test_sync_missing_kb_agent_path(self):
        non_existent_path = self.temp_path / "non_existent"
        adapter = ScrapyKBAdapter(
            kb_agent_path=non_existent_path,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )
        res = adapter.sync()
        self.assertEqual(res["status"], "error")
        self.assertIn("not found", res["message"])

    def test_sync_success_and_metadata_validation(self):
        # Create a mock markdown file with missing metadata inside C64-KB-Agent
        test_file = self.kb_scraped_dir / "assembly_lesson_1.md"
        post_content = "Here is some raw assembly knowledge."
        post = frontmatter.Post(post_content)
        # Empty metadata
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )

        # Run sync
        res = adapter.sync()
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["synced"], 1)
        self.assertEqual(res["new"], 1)

        # Verify destination file exists and metadata is enriched
        dest_file = self.dest_kb_dir / "assembly_lesson_1.md"
        self.assertTrue(dest_file.exists())

        with open(dest_file, "r", encoding="utf-8") as f:
            synced_post = frontmatter.load(f)

        self.assertEqual(synced_post.content, post_content)
        self.assertEqual(synced_post.metadata.get("title"), "Assembly Lesson 1")
        self.assertEqual(synced_post.metadata.get("tags"), ["c64", "scraped"])

    def test_sync_deduplication_via_hash(self):
        test_file = self.kb_scraped_dir / "sprite_tutorial.md"
        post = frontmatter.Post("Learn VIC-II sprites.", title="Sprite Tutorial", tags=["c64", "sprites"])
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )

        # First sync
        res_first = adapter.sync()
        self.assertEqual(res_first["synced"], 1)
        self.assertEqual(res_first["new"], 1)

        # Second sync without changes
        res_second = adapter.sync()
        self.assertEqual(res_second["synced"], 0)
        self.assertEqual(res_second["unchanged"], 1)

        # Modify file and sync again (should detect update)
        with open(test_file, "w", encoding="utf-8") as f:
            post.content = "Updated content for sprites."
            f.write(frontmatter.dumps(post))

        res_third = adapter.sync()
        self.assertEqual(res_third["synced"], 1)
        self.assertEqual(res_third["updated"], 1)

    @patch("subprocess.run")
    def test_run_scrapy_spider_success(self, mock_run):
        # Configure mocked subprocess
        mock_proc = MagicMock()
        mock_proc.stdout = "Scrapy completed successfully"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )

        res = adapter.run_scrapy_spider("c64_wiki")
        self.assertEqual(res["status"], "ok")
        self.assertIn("Scrapy completed", res["spider_stdout"])
        mock_run.assert_called_once_with(
            ["scrapy", "crawl", "c64_wiki"],
            cwd=self.scrapy_dir,
            capture_output=True,
            text=True,
            check=True
        )

    @patch("subprocess.run")
    def test_run_scrapy_spider_failure(self, mock_run):
        import subprocess
        # Simulate subprocess failure
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["scrapy", "crawl", "c64_wiki"],
            stderr="Crawling error"
        )

        adapter = ScrapyKBAdapter(
            kb_agent_path=self.kb_agent_dir,
            scrapy_path=self.scrapy_dir,
            dest_kb_path=self.dest_kb_dir
        )

        res = adapter.run_scrapy_spider("c64_wiki")
        self.assertEqual(res["status"], "error")
        self.assertIn("Spider run failed", res["message"])

if __name__ == "__main__":
    unittest.main()

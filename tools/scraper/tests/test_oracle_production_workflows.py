from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = (
    ROOT / ".github/workflows/deploy-pages.yml",
    ROOT / ".github/workflows/scrape-data.yml",
)


class OracleProductionWorkflowTests(unittest.TestCase):
    def test_production_uses_hardened_downloader_and_48_hour_cache(self) -> None:
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                workflow: dict[str, Any] = yaml.load(text, Loader=yaml.BaseLoader)
                commands = "\n".join(
                    step.get("run", "")
                    for job in workflow["jobs"].values()
                    for step in job.get("steps", [])
                )
                resolver_command = next(
                    step["run"]
                    for job in workflow["jobs"].values()
                    for step in job.get("steps", [])
                    if step.get("id") == "oracle_download"
                )
                self.assertEqual(workflow["env"]["ORACLE_CACHE_MAX_AGE_HOURS"], "48")
                self.assertIn("python -m loltee_scraper.oracle_download", commands)
                self.assertIn("--require-production-current", commands)
                self.assertIn("--oracle-metadata", commands)
                self.assertNotIn("is_recent_for_bet_ai", text)
                self.assertNotIn("snapshot", resolver_command.lower())
                self.assertNotIn("curl ", resolver_command)
                self.assertNotIn("fetched_at", resolver_command)

    def test_cache_is_saved_only_after_a_live_validated_download(self) -> None:
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
                job = next(iter(workflow["jobs"].values()))
                save = next(
                    step for step in job["steps"]
                    if step.get("uses", "").startswith("actions/cache/save@")
                )
                self.assertEqual(
                    save["if"],
                    "steps.oracle_download.outputs.cache_updated == 'true'",
                )

    def test_summary_reports_both_freshness_clocks(self) -> None:
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                for field in (
                    "State/source",
                    "Downloaded at",
                    "Download age",
                    "Last match at",
                    "Match-data age",
                    "Content changed",
                    "Patches used",
                ):
                    self.assertIn(field, text)


if __name__ == "__main__":
    unittest.main()

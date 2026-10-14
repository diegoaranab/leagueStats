from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github/workflows/oracle-download-validation.yml"
)


class OracleDownloadWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.workflow: dict[str, Any] = yaml.load(
            cls.workflow_text, Loader=yaml.BaseLoader,
        )
        cls.job = cls.workflow["jobs"]["validate-oracle-download"]

    def test_workflow_is_manual_only_and_read_only(self) -> None:
        self.assertEqual(self.workflow["on"], {"workflow_dispatch": ""})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        self.assertNotIn("schedule", self.workflow_text)
        self.assertNotIn("push:", self.workflow_text)

    def test_workflow_uses_isolated_downloader_with_24_hour_threshold(self) -> None:
        commands = "\n".join(step.get("run", "") for step in self.job["steps"])
        self.assertIn("python -m loltee_scraper.oracle_download", commands)
        self.assertIn("--bet-ai-max-data-age-hours", commands)
        self.assertEqual(self.job["env"]["BET_AI_MAX_DATA_AGE_HOURS"], "24")
        self.assertIn("content_changed", commands)
        self.assertIn("is_recent_for_bet_ai", commands)

    def test_retry_budget_leaves_time_for_every_source_and_reporting(self) -> None:
        attempts = int(self.job["env"]["ORACLE_DOWNLOAD_ATTEMPTS"])
        timeout_seconds = int(
            self.job["env"]["ORACLE_DOWNLOAD_TIMEOUT_SECONDS"]
        )
        backoff_seconds = int(
            self.job["env"]["ORACLE_DOWNLOAD_BACKOFF_SECONDS"]
        )
        remote_sources = 4  # direct, alternate, gdown, and snapshot
        backoff_per_source = backoff_seconds * (2 ** (attempts - 1) - 1)
        worst_case_download_seconds = remote_sources * (
            attempts * timeout_seconds + backoff_per_source
        )
        job_seconds = int(self.job["timeout-minutes"]) * 60

        self.assertLessEqual(worst_case_download_seconds, job_seconds - 300)
        self.assertEqual(attempts, 2)
        self.assertEqual(timeout_seconds, 60)

    def test_workflow_does_not_generate_or_publish_application_data(self) -> None:
        forbidden = (
            "deploy-pages",
            "deploy-pages@",
            "build_teamplay",
            "run_matrix",
            "apps/web/public",
            "git push",
        )
        lowered = self.workflow_text.lower()
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, lowered)

        actions = {
            step.get("uses", "").split("@")[0]
            for step in self.job["steps"]
            if step.get("uses")
        }
        self.assertEqual(
            actions,
            {
                "actions/checkout",
                "actions/setup-python",
                "actions/cache/restore",
                "actions/cache/save",
                "actions/upload-artifact",
            },
        )


if __name__ == "__main__":
    unittest.main()

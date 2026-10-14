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

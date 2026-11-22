from __future__ import annotations

import unittest
from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github/workflows/oracle-download-validation.yml"


class OracleDownloadWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.workflow = yaml.load(cls.text, Loader=yaml.BaseLoader)
        cls.job = cls.workflow["jobs"]["validate-oracle-download"]

    def test_manual_read_only(self):
        self.assertEqual(self.workflow["on"], {"workflow_dispatch": ""})
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_authenticated_step_has_scoped_secrets(self):
        steps = self.job["steps"]
        authenticated = next(step for step in steps if "loltee_scraper.oracle_drive_api" in step.get("run", ""))
        for name in ("GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN"):
            self.assertEqual(authenticated["env"][name], "${{ secrets." + name + " }}")
            self.assertNotIn(name, self.job.get("env", {}))
            self.assertEqual(sum(name in step.get("env", {}) for step in steps), 1)
        self.assertEqual(set(self.job.get("env", {})), set())
        self.assertNotIn("data_age_seconds", self.text)

    def test_no_fallback_or_application_writes(self):
        for value in ("actions/cache", "snapshot", "gdown", "drive.google.com/uc", "drive.usercontent.google.com", "oracle_download ", "build_teamplay", "run_matrix", "apps/", "deploy", "git push"):
            with self.subTest(value=value):
                self.assertNotIn(value, self.text.lower())
        actions = {step["uses"].split("@")[0] for step in self.job["steps"] if "uses" in step}
        self.assertEqual(actions, {"actions/checkout", "actions/setup-python", "actions/upload-artifact"})
        uploads = [step for step in self.job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@")]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with"]["path"], "${{ runner.temp }}/oracle-download/metadata.json")


if __name__ == "__main__":
    unittest.main()

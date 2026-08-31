from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "deploy-pages.yml"
MIDNIGHT_CRON = "23 0 * * *"
NOON_CRON = "23 12 * * *"
MIDNIGHT_HISTORY_CONDITION = (
    "${{ always() && github.event_name == 'schedule' && "
    "github.event.schedule == '23 0 * * *' }}"
)
HISTORY_ARTIFACT = "difficulty-history-solo-matrix"


class DeployWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.workflow: dict[str, Any] = yaml.load(
            cls.workflow_text,
            Loader=yaml.BaseLoader,
        )
        cls.jobs = cls.workflow["jobs"]

    @staticmethod
    def step_named(job: dict[str, Any], name: str) -> dict[str, Any]:
        return next(step for step in job["steps"] if step.get("name") == name)

    def test_midnight_history_runs_after_a_failed_build(self) -> None:
        history_job = self.jobs["persist-difficulty-history"]

        self.assertEqual(history_job["needs"], "build")
        self.assertEqual(history_job["if"], MIDNIGHT_HISTORY_CONDITION)
        self.assertIn("always()", history_job["if"])
        self.assertNotIn("needs.build.result", history_job["if"])

    def test_missing_history_artifact_fails_persistence(self) -> None:
        history_job = self.jobs["persist-difficulty-history"]
        download = self.step_named(history_job, "Download complete Solo matrix")
        merge = self.step_named(history_job, "Merge daily Solo observations")

        self.assertEqual(download["uses"], "actions/download-artifact@v4")
        self.assertEqual(download["with"]["name"], HISTORY_ARTIFACT)
        self.assertNotIn("continue-on-error", download)
        self.assertNotIn("if", download)
        self.assertLess(
            history_job["steps"].index(download),
            history_job["steps"].index(merge),
        )

        upload = self.step_named(
            self.jobs["build"],
            "Upload Solo matrix for difficulty history",
        )
        self.assertEqual(upload["with"]["name"], HISTORY_ARTIFACT)
        self.assertEqual(upload["with"]["if-no-files-found"], "error")

    def test_normal_runs_cannot_cancel_midnight_history(self) -> None:
        self.assertNotIn("concurrency", self.workflow)
        self.assertNotIn("concurrency", self.jobs["build"])
        self.assertNotIn("concurrency", self.jobs["persist-difficulty-history"])

    def test_pages_deployments_are_serialized(self) -> None:
        deployment_concurrency = self.jobs["deploy"]["concurrency"]

        self.assertEqual(deployment_concurrency["group"], "pages")
        self.assertEqual(deployment_concurrency["cancel-in-progress"], "true")

    def test_only_midnight_schedule_mutates_history(self) -> None:
        schedules = self.workflow["on"]["schedule"]
        self.assertEqual(
            {entry["cron"] for entry in schedules},
            {MIDNIGHT_CRON, NOON_CRON},
        )

        history_job = self.jobs["persist-difficulty-history"]
        upload = self.step_named(
            self.jobs["build"],
            "Upload Solo matrix for difficulty history",
        )
        self.assertEqual(history_job["if"], MIDNIGHT_HISTORY_CONDITION)
        self.assertEqual(
            upload["if"],
            "${{ github.event_name == 'schedule' && "
            "github.event.schedule == '23 0 * * *' }}",
        )

        history_writers = [
            job_name
            for job_name, job in self.jobs.items()
            if "git push origin HEAD:difficulty-history"
            in "\n".join(step.get("run", "") for step in job["steps"])
        ]
        self.assertEqual(history_writers, ["persist-difficulty-history"])


if __name__ == "__main__":
    unittest.main()

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
        concurrency = self.workflow["concurrency"]
        triggers = self.workflow["on"]

        self.assertEqual(concurrency["group"], "pages")
        self.assertEqual(concurrency["cancel-in-progress"], "false")
        self.assertIn("push", triggers)
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(
            {entry["cron"] for entry in triggers["schedule"]},
            {MIDNIGHT_CRON, NOON_CRON},
        )

    def test_entire_workflow_is_serialized_in_one_shared_group(self) -> None:
        concurrency = self.workflow["concurrency"]

        self.assertEqual(concurrency, {
            "group": "pages",
            "cancel-in-progress": "false",
        })
        for job in self.jobs.values():
            self.assertNotIn("concurrency", job)

    def test_builds_and_deployments_cannot_overlap_or_reorder(self) -> None:
        self.assertEqual(self.workflow["concurrency"]["group"], "pages")
        self.assertEqual(
            self.workflow["concurrency"]["cancel-in-progress"],
            "false",
        )
        self.assertEqual(
            self.jobs["deploy"]["needs"],
            ["build", "persist-difficulty-history"],
        )

    def test_pages_deployment_requires_successful_build_output(self) -> None:
        build = self.jobs["build"]
        deploy = self.jobs["deploy"]
        upload = self.step_named(build, "Upload Pages artifact")
        deployment = self.step_named(deploy, "Deploy Pages artifact")

        self.assertIn("build", deploy["needs"])
        self.assertEqual(
            deploy["if"],
            "${{ always() && !cancelled() && needs.build.result == 'success' }}",
        )
        self.assertEqual(upload["uses"], "actions/upload-pages-artifact@v3")
        self.assertEqual(deployment["uses"], "actions/deploy-pages@v4")

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

    def test_all_solo_builds_load_history_read_only_with_bootstrap_fallback(self) -> None:
        build = self.jobs["build"]
        load = self.step_named(build, "Load difficulty history for scoring")
        generate = self.step_named(build, "Generate Solo Queue datasets")

        self.assertNotIn("if", load)
        self.assertLess(build["steps"].index(load), build["steps"].index(generate))
        self.assertIn("git ls-remote --exit-code --heads origin difficulty-history", load["run"])
        self.assertIn("git show FETCH_HEAD:difficulty-history.json", load["run"])
        self.assertIn("using snapshot fallback", load["run"])
        self.assertNotIn("git push", load["run"])
        self.assertNotIn("git switch", load["run"])

        self.assertIn("--difficulty-history-file", generate["run"])
        self.assertIn('if [[ -f "$HISTORY_FILE" ]]', generate["run"])


if __name__ == "__main__":
    unittest.main()

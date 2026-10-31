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

    def test_normal_runs_cannot_cancel_scheduled_refresh(self) -> None:
        self.assertEqual(
            self.workflow["concurrency"],
            {"group": "pages", "cancel-in-progress": "false"},
        )
        for job in self.jobs.values():
            self.assertNotIn("concurrency", job)

        triggers = self.workflow["on"]
        self.assertIn("push", triggers)
        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(
            {entry["cron"] for entry in triggers["schedule"]},
            {MIDNIGHT_CRON, NOON_CRON},
        )

    def test_push_source_selection_reuses_only_a_valid_snapshot(self) -> None:
        prepare = self.jobs["prepare-data"]
        selection = self.step_named(prepare, "Select production data source")
        command = selection["run"]

        self.assertIn('[[ "$EVENT_NAME" == "push" ]]', command)
        self.assertIn("git ls-remote --exit-code --heads origin production-data", command)
        self.assertIn("git archive refs/remotes/origin/production-data data", command)
        self.assertIn("validate-production-data.py", command)
        self.assertIn("refresh=false", command)
        self.assertIn('reason="the production-data snapshot is invalid"', command)
        self.assertIn('reason="the production-data branch does not exist yet"', command)

    def test_data_sensitive_changes_force_refresh(self) -> None:
        selection = self.step_named(
            self.jobs["prepare-data"],
            "Select production data source",
        )["run"]
        for path in (
            "tools/scraper/*",
            ".github/workflows/deploy-pages.yml",
            ".github/scripts/validate-production-data.py",
            "apps/web/src/app/core/models/tierlist.model.ts",
            "apps/web/src/app/core/services/tierlist.service.ts",
        ):
            self.assertIn(path, selection)

    def test_schedule_and_manual_dispatch_default_to_full_refresh(self) -> None:
        selection = self.step_named(
            self.jobs["prepare-data"],
            "Select production data source",
        )["run"]
        self.assertIn("refresh=true", selection)
        self.assertNotIn("workflow_dispatch.inputs", self.workflow_text)

        generate = self.step_named(
            self.jobs["prepare-data"],
            "Generate Solo Queue datasets",
        )
        self.assertEqual(generate["if"], "steps.data_source.outputs.refresh == 'true'")

    def test_refresh_preserves_oracle_and_history_safety(self) -> None:
        prepare = self.jobs["prepare-data"]
        resolver = self.step_named(prepare, "Resolve Oracle's Elixir CSV")
        load = self.step_named(prepare, "Load difficulty history for scoring")
        generate = self.step_named(prepare, "Generate Solo Queue datasets")

        self.assertIn("--require-production-current", resolver["run"])
        self.assertIn("git ls-remote --exit-code --heads origin difficulty-history", load["run"])
        self.assertIn("git show FETCH_HEAD:difficulty-history.json", load["run"])
        self.assertIn("using snapshot fallback", load["run"])
        self.assertNotIn("git push", load["run"])
        self.assertLess(prepare["steps"].index(load), prepare["steps"].index(generate))
        self.assertIn("--difficulty-history-file", generate["run"])

    def test_snapshot_is_persisted_only_after_complete_validation(self) -> None:
        prepare = self.jobs["prepare-data"]
        validate = self.step_named(prepare, "Validate selected production data")
        upload = self.step_named(prepare, "Upload validated production data")
        persist = self.jobs["persist-production-data"]

        self.assertLess(prepare["steps"].index(validate), prepare["steps"].index(upload))
        self.assertEqual(persist["needs"], "prepare-data")
        self.assertEqual(persist["if"], "needs.prepare-data.outputs.refreshed == 'true'")
        self.assertEqual(persist["permissions"], {"contents": "write"})
        self.assertIn(
            "git push origin HEAD:production-data",
            self.step_named(persist, "Commit validated snapshot only when changed")["run"],
        )
        self.assertEqual(prepare["permissions"], {"contents": "read"})

    def test_fast_build_has_no_scraper_toolchain(self) -> None:
        build = self.jobs["build"]
        step_names = {step["name"] for step in build["steps"]}
        self.assertNotIn("Setup Python", step_names)
        self.assertNotIn("Install Playwright Chromium", step_names)
        self.assertIn("Download selected production data", step_names)
        self.assertFalse(any("python" in step.get("run", "") for step in build["steps"]))

        self.assertEqual(build["needs"], ["prepare-data", "persist-production-data"])
        self.assertIn("needs.persist-production-data.result == 'success'", build["if"])
        self.assertIn("needs.persist-production-data.result == 'skipped'", build["if"])

    def test_missing_history_artifact_fails_persistence(self) -> None:
        history_job = self.jobs["persist-difficulty-history"]
        download = self.step_named(history_job, "Download complete Solo matrix")
        merge = self.step_named(history_job, "Merge daily Solo observations")
        upload = self.step_named(
            self.jobs["prepare-data"],
            "Upload Solo matrix for difficulty history",
        )

        self.assertEqual(download["uses"], "actions/download-artifact@v4")
        self.assertEqual(download["with"]["name"], HISTORY_ARTIFACT)
        self.assertNotIn("continue-on-error", download)
        self.assertNotIn("if", download)
        self.assertLess(history_job["steps"].index(download), history_job["steps"].index(merge))
        self.assertEqual(upload["with"]["name"], HISTORY_ARTIFACT)
        self.assertEqual(upload["with"]["if-no-files-found"], "error")

    def test_only_midnight_schedule_mutates_history_from_fresh_solo_data(self) -> None:
        history_job = self.jobs["persist-difficulty-history"]
        upload = self.step_named(
            self.jobs["prepare-data"],
            "Upload Solo matrix for difficulty history",
        )
        self.assertEqual(history_job["needs"], "prepare-data")
        self.assertEqual(history_job["if"], MIDNIGHT_HISTORY_CONDITION)
        self.assertIn("steps.data_source.outputs.refresh == 'true'", upload["if"])
        self.assertIn("github.event.schedule == '23 0 * * *'", upload["if"])

        history_writers = [
            job_name
            for job_name, job in self.jobs.items()
            if "git push origin HEAD:difficulty-history"
            in "\n".join(step.get("run", "") for step in job["steps"])
        ]
        self.assertEqual(history_writers, ["persist-difficulty-history"])

    def test_pages_deployment_requires_successful_build_output(self) -> None:
        build = self.jobs["build"]
        deploy = self.jobs["deploy"]
        upload = self.step_named(build, "Upload Pages artifact")
        deployment = self.step_named(deploy, "Deploy Pages artifact")

        self.assertEqual(deploy["needs"], ["build", "persist-difficulty-history"])
        self.assertEqual(
            deploy["if"],
            "${{ always() && !cancelled() && needs.build.result == 'success' }}",
        )
        self.assertEqual(upload["uses"], "actions/upload-pages-artifact@v3")
        self.assertEqual(deployment["uses"], "actions/deploy-pages@v4")


if __name__ == "__main__":
    unittest.main()

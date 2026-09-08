from __future__ import annotations

import unittest
from pathlib import Path

import yaml


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github/workflows/pr-validation.yml"
)


class PRWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # BaseLoader preserves GitHub's `on` key instead of treating it as a boolean.
        cls.workflow = yaml.load(
            WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader,
        )
        cls.jobs = cls.workflow["jobs"]

    def test_all_pull_requests_to_main_are_validated(self) -> None:
        triggers = self.workflow["on"]
        self.assertEqual(triggers["pull_request"], {"branches": ["main"]})
        self.assertLessEqual(set(triggers), {"pull_request", "workflow_dispatch"})

    def test_permissions_are_read_only(self) -> None:
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        for job in self.jobs.values():
            self.assertEqual(
                job.get("permissions", self.workflow["permissions"]),
                {"contents": "read"},
            )

    def test_python_suite_and_compilation_run(self) -> None:
        job = self.jobs["python"]
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        commands = " ".join(commands.replace("\\\n", " ").split())
        self.assertIn("pip install -e tools/scraper", commands)
        self.assertIn("python -m unittest discover -s tools/scraper/tests -v", commands)
        self.assertIn("python -m compileall -q tools/scraper/src tools/scraper/tests", commands)

    def test_frontend_installs_lockfile_and_builds_production(self) -> None:
        job = self.jobs["frontend"]
        commands = {step.get("run", ""): step for step in job["steps"]}
        for command in (
            "npm ci", "npm run build -- --configuration production --base-href /",
        ):
            step = commands[command]
            directory = step.get(
                "working-directory",
                job.get("defaults", {}).get("run", {}).get("working-directory"),
            )
            self.assertEqual(directory, "apps/web")

    def test_validation_is_unconditional_and_failures_are_reported(self) -> None:
        for job in self.jobs.values():
            for node in (job, *job["steps"]):
                self.assertNotIn("if", node)
                self.assertNotEqual(node.get("continue-on-error"), "true")

    def test_no_deployment_or_live_data_operations(self) -> None:
        for job in self.jobs.values():
            self.assertNotIn("uses", job)
            self.assertNotIn("environment", job)
            self.assertNotIn("matrix", job.get("strategy", {}))
            for step in job["steps"]:
                action = step.get("uses", "").split("@")[0]
                if action:
                    self.assertIn(action, {
                        "actions/checkout", "actions/setup-python", "actions/setup-node",
                    })
                command = step.get("run", "").lower()
                for forbidden in (
                    "git push", "difficulty_history", "difficulty-history",
                    "run_matrix", "loltee-scrape", "loltee_scraper.cli",
                    "build_teamplay", "oracle", "gdown", "curl ", "wget ",
                    "playwright install",
                ):
                    with self.subTest(forbidden=forbidden):
                        self.assertNotIn(forbidden, command)

    def test_obsolete_runs_are_cancelled_per_pull_request(self) -> None:
        concurrency = self.workflow["concurrency"]
        self.assertEqual(concurrency["cancel-in-progress"], "true")
        self.assertIn("github.event.pull_request.number", concurrency["group"])
        self.assertIn("github.ref", concurrency["group"])
        self.assertTrue(concurrency["group"].startswith("pr-validation-"))


if __name__ == "__main__":
    unittest.main()

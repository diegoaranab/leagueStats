from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = REPOSITORY_ROOT / ".github" / "scripts" / "validate-production-data.py"


class ProductionDataValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.write_snapshot()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def write_snapshot(self) -> None:
        entries = []
        for mode, prefix in (("solo", Path()), ("teamplay", Path("teamplay"))):
            relative = prefix / "na" / "iron" / "current.json"
            public_path = f"/data/{relative.as_posix()}"
            entries.append(
                {
                    "mode": mode,
                    "region": "na",
                    "tier": "iron",
                    "window": "current",
                    "path": public_path,
                    "status": "ok",
                    "is_partial": False,
                    "failed_lanes": [],
                    "champion_count": 1,
                }
            )
            self.write_json(
                self.root / relative,
                {
                    "meta": {"is_partial": False, "failed_lanes": []},
                    "data": {"top": [{"name": "Aatrox"}]},
                },
            )

        self.write_json(
            self.root / "manifest.json",
            {
                "supported": {
                    "regions": ["na"],
                    "tiers": ["iron"],
                    "windows": ["current"],
                    "lanes": ["top"],
                    "modes": ["solo", "teamplay"],
                },
                "datasets": entries,
            },
        )

    def run_validator(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--root",
                str(self.root),
                "--regions",
                "na",
                "--tiers",
                "iron",
                "--windows",
                "current",
                "--lanes",
                "top",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_accepts_complete_solo_and_teamplay_snapshot(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 2 deployable production datasets", result.stdout)

    def test_accepts_warning_level_teamplay_partial(self) -> None:
        warning = (
            "Oracle competitive slice includes rows where "
            "datacompleteness != 'complete'."
        )
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        teamplay = manifest["datasets"][1]
        teamplay.update(
            {
                "status": "partial",
                "is_partial": True,
                "failed_lanes": [],
                "champion_count": 1,
                "warnings": [warning],
            }
        )
        self.write_json(self.root / "manifest.json", manifest)

        dataset_path = self.root / "teamplay" / "na" / "iron" / "current.json"
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        dataset["meta"].update(
            {"is_partial": True, "failed_lanes": [], "warnings": [warning]}
        )
        self.write_json(dataset_path, dataset)

        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Validated 2 deployable production datasets", result.stdout)

    def test_rejects_missing_teamplay_dataset(self) -> None:
        (self.root / "teamplay" / "na" / "iron" / "current.json").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read valid JSON", result.stderr)

    def test_rejects_failed_lane_partial(self) -> None:
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["datasets"][0]["status"] = "partial"
        manifest["datasets"][0]["is_partial"] = True
        manifest["datasets"][0]["failed_lanes"] = ["top"]
        self.write_json(self.root / "manifest.json", manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reports failed lanes", result.stderr)

    def test_rejects_failed_lane_reported_by_dataset_metadata(self) -> None:
        dataset_path = self.root / "teamplay" / "na" / "iron" / "current.json"
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        dataset["meta"].update({"is_partial": True, "failed_lanes": ["top"]})
        self.write_json(dataset_path, dataset)

        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["datasets"][1].update(
            {"status": "partial", "is_partial": True, "failed_lanes": []}
        )
        self.write_json(self.root / "manifest.json", manifest)

        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reports failed lanes", result.stderr)

    def test_rejects_error_dataset(self) -> None:
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["datasets"][1]["status"] = "error"
        manifest["datasets"][1]["is_partial"] = True
        self.write_json(self.root / "manifest.json", manifest)

        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non-deployable status 'error'", result.stderr)

    def test_rejects_corrupt_dataset(self) -> None:
        dataset_path = self.root / "teamplay" / "na" / "iron" / "current.json"
        dataset_path.write_text("{not-json", encoding="utf-8")

        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()

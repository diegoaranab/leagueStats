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
        self.assertIn("Validated 2 complete production datasets", result.stdout)

    def test_rejects_missing_teamplay_dataset(self) -> None:
        (self.root / "teamplay" / "na" / "iron" / "current.json").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read valid JSON", result.stderr)

    def test_rejects_partial_dataset(self) -> None:
        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        manifest["datasets"][0]["status"] = "partial"
        manifest["datasets"][0]["is_partial"] = True
        self.write_json(self.root / "manifest.json", manifest)
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not complete", result.stderr)


if __name__ == "__main__":
    unittest.main()

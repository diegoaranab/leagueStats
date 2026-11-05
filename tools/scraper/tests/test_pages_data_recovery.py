from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECOVERY_SCRIPT = REPOSITORY_ROOT / ".github" / "scripts" / "recover-pages-data.py"
VALIDATOR = REPOSITORY_ROOT / ".github" / "scripts" / "validate-production-data.py"


def load_recovery_module():
    spec = importlib.util.spec_from_file_location("recover_pages_data", RECOVERY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {RECOVERY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    def read(self, size: int) -> bytes:
        return self.payload[:size]


class FakeOpener:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses

    def open(self, request, timeout: int) -> FakeResponse:
        try:
            return FakeResponse(self.responses[request.full_url])
        except KeyError as exc:
            raise OSError(f"unexpected URL {request.full_url}") from exc


class PagesDataRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.site_root = self.root / "site" / "leagueStats" / "data"
        self.write_deployed_snapshot()
        self.base_url = "https://example.test/leagueStats/"
        self.recovery_module = load_recovery_module()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def write_json(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def write_deployed_snapshot(self) -> None:
        warning = (
            "Oracle competitive slice includes rows where "
            "datacompleteness != 'complete'."
        )
        entries = []
        for mode, prefix in (("solo", Path()), ("teamplay", Path("teamplay"))):
            relative = prefix / "na" / "iron" / "current.json"
            partial = mode == "teamplay"
            entries.append(
                {
                    "mode": mode,
                    "region": "na",
                    "tier": "iron",
                    "window": "current",
                    "path": f"/data/{relative.as_posix()}",
                    "status": "partial" if partial else "ok",
                    "is_partial": partial,
                    "failed_lanes": [],
                    "warnings": [warning] if partial else [],
                    "champion_count": 1,
                }
            )
            self.write_json(
                self.site_root / relative,
                {
                    "meta": {
                        "is_partial": partial,
                        "failed_lanes": [],
                        "warnings": [warning] if partial else [],
                    },
                    "data": {"top": [{"name": "Aatrox"}]},
                },
            )

        self.write_json(
            self.site_root / "manifest.json",
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

    def fake_opener(self) -> FakeOpener:
        responses = {}
        for path in self.site_root.rglob("*.json"):
            relative = path.relative_to(self.site_root).as_posix()
            responses[f"{self.base_url}data/{relative}"] = path.read_bytes()
        return FakeOpener(responses)

    def run_recovery(self, output_root: Path) -> None:
        args = argparse.Namespace(
            base_url=self.base_url,
            output_root=output_root,
            regions=["na"],
            tiers=["iron"],
            windows=["current"],
            lanes=["top"],
        )
        with mock.patch.object(
            self.recovery_module.urllib.request,
            "build_opener",
            return_value=self.fake_opener(),
        ):
            self.recovery_module.recover(args)

    def run_validator(self, output_root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--root",
                str(output_root),
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

    def test_recovers_and_validates_warning_level_pages_snapshot(self) -> None:
        output_root = self.root / "recovered"
        self.run_recovery(output_root)
        self.assertTrue((output_root / "manifest.json").is_file())
        self.assertTrue((output_root / "teamplay" / "na" / "iron" / "current.json").is_file())

        validation = self.run_validator(output_root)
        self.assertEqual(validation.returncode, 0, validation.stderr)
        self.assertIn("Validated 2 deployable production datasets", validation.stdout)

    def test_rejects_manifest_path_outside_expected_data_matrix(self) -> None:
        manifest_path = self.site_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["datasets"][1]["path"] = "/data/../../arbitrary.json"
        self.write_json(manifest_path, manifest)

        output_root = self.root / "recovered"
        with self.assertRaisesRegex(ValueError, "has unsafe path"):
            self.run_recovery(output_root)
        self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()

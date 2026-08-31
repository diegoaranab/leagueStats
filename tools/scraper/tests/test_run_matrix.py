from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loltee_scraper.difficulty_history import HistoryValidationError
from loltee_scraper import run_matrix


class RunMatrixDifficultyHistoryTests(unittest.TestCase):
    def test_history_is_loaded_once_and_reused_for_every_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            history_path = root / "difficulty-history.json"
            history_path.write_text("placeholder", encoding="utf-8")
            loaded_history = {"series": {}}
            received_histories: list[object] = []

            def fake_scrape_to_file(*, config, headless, difficulty_history):
                received_histories.append(difficulty_history)
                return {
                    "meta": {
                        "generated_at_utc": "2026-08-30T12:23:00+00:00",
                        "is_partial": False,
                        "failed_lanes": [],
                        "warnings": [],
                    },
                    "data": {},
                }

            arguments = [
                "run_matrix",
                "--output-root",
                str(root / "output"),
                "--regions",
                "lan",
                "--tiers",
                "gold",
                "--windows",
                "7d",
                "14d",
                "--lanes",
                "middle",
                "--difficulty-history-file",
                str(history_path),
            ]
            with (
                patch("sys.argv", arguments),
                patch.object(run_matrix, "load_history", return_value=loaded_history) as load,
                patch.object(run_matrix, "scrape_to_file", side_effect=fake_scrape_to_file),
            ):
                run_matrix.main()

            load.assert_called_once_with(history_path)
            self.assertEqual(len(received_histories), 2)
            self.assertTrue(all(item is loaded_history for item in received_histories))

    def test_malformed_explicit_history_fails_before_scraping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            history_path = root / "difficulty-history.json"
            history_path.write_text("{}", encoding="utf-8")
            arguments = [
                "run_matrix",
                "--output-root",
                str(root / "output"),
                "--regions",
                "lan",
                "--tiers",
                "gold",
                "--windows",
                "7d",
                "--lanes",
                "middle",
                "--difficulty-history-file",
                str(history_path),
            ]

            with (
                patch("sys.argv", arguments),
                patch.object(run_matrix, "scrape_to_file") as scrape,
                self.assertRaises(HistoryValidationError),
            ):
                run_matrix.main()

            scrape.assert_not_called()

    def test_missing_explicit_history_fails_visibly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            arguments = [
                "run_matrix",
                "--output-root",
                str(root / "output"),
                "--regions",
                "lan",
                "--tiers",
                "gold",
                "--windows",
                "7d",
                "--lanes",
                "middle",
                "--difficulty-history-file",
                str(root / "missing.json"),
            ]

            with patch("sys.argv", arguments), self.assertRaises(SystemExit) as raised:
                run_matrix.main()

            self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

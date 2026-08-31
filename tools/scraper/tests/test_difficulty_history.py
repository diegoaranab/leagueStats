from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from loltee_scraper.difficulty_history import (
    HistoryValidationError,
    load_history,
    merge_solo_matrix,
    new_history,
    serialize_history,
    write_history,
)


REGIONS = ["na"]
TIERS = ["gold"]
WINDOWS = ["7d"]
LANES = ["top", "middle"]
FIXED_UPDATE_TIME = datetime(2026, 8, 30, 0, 30, tzinfo=timezone.utc)


def champion(
    name: str,
    *,
    delta: float | None = 4.2,
    win_rate: float | None = 51.5,
    mastery_gap_pct: float | None = 8.1,
) -> dict[str, object]:
    return {
        "name": name,
        "delta": delta,
        "win_rate": win_rate,
        "mastery_gap_pct": mastery_gap_pct,
    }


def write_dataset(
    root: Path,
    *,
    top: list[dict[str, object]] | None = None,
    middle: list[dict[str, object]] | None = None,
    partial: bool = False,
) -> None:
    path = root / "na" / "gold" / "7d.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "meta": {
                    "region": "na",
                    "tier": "gold",
                    "window": "7d",
                    "is_partial": partial,
                    "failed_lanes": ["top"] if partial else [],
                },
                "data": {
                    "top": top or [],
                    "middle": middle or [],
                },
            }
        ),
        encoding="utf-8",
    )


def merge_fixture(
    history: dict[str, object],
    root: Path,
    day: date,
    *,
    lanes: list[str] = LANES,
) -> dict[str, object]:
    return merge_solo_matrix(
        history,
        root,
        regions=REGIONS,
        tiers=TIERS,
        windows=WINDOWS,
        lanes=lanes,
        observation_date=day,
        updated_at_utc=FIXED_UPDATE_TIME,
    )


class DifficultyHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_first_observation_creates_series(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox")])

        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))

        self.assertEqual(
            history["series"]["na|gold|7d|top|Aatrox"],
            [
                {
                    "date": "2026-08-01",
                    "delta": 4.2,
                    "win_rate": 51.5,
                    "mastery_gap_pct": 8.1,
                }
            ],
        )

    def test_second_day_appends(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=8.1)])
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=8.5)])

        history = merge_fixture(history, self.root, date(2026, 8, 2))

        self.assertEqual(
            [item["date"] for item in history["series"]["na|gold|7d|top|Aatrox"]],
            ["2026-08-01", "2026-08-02"],
        )

    def test_same_day_replaces_instead_of_duplicating(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=8.1)])
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=9.7)])

        history = merge_fixture(history, self.root, date(2026, 8, 1))

        observations = history["series"]["na|gold|7d|top|Aatrox"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["mastery_gap_pct"], 9.7)

    def test_same_day_missing_champion_removes_current_observation(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox")])
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root)

        history = merge_fixture(history, self.root, date(2026, 8, 1))

        self.assertNotIn("na|gold|7d|top|Aatrox", history["series"])

    def test_same_day_null_mastery_gap_removes_current_observation(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox")])
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=None)])

        history = merge_fixture(history, self.root, date(2026, 8, 1))

        self.assertNotIn("na|gold|7d|top|Aatrox", history["series"])

    def test_same_day_replacement_preserves_prior_day_observation(self) -> None:
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=8.1)])
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=8.5)])
        history = merge_fixture(history, self.root, date(2026, 8, 2))
        write_dataset(self.root)

        history = merge_fixture(history, self.root, date(2026, 8, 2))

        self.assertEqual(
            history["series"]["na|gold|7d|top|Aatrox"],
            [
                {
                    "date": "2026-08-01",
                    "delta": 4.2,
                    "win_rate": 51.5,
                    "mastery_gap_pct": 8.1,
                }
            ],
        )

    def test_same_day_replacement_preserves_unrequested_lane(self) -> None:
        write_dataset(
            self.root,
            top=[champion("Aatrox", mastery_gap_pct=8.1)],
            middle=[champion("Ahri", mastery_gap_pct=12.4)],
        )
        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        write_dataset(self.root)

        history = merge_fixture(
            history,
            self.root,
            date(2026, 8, 1),
            lanes=["top"],
        )

        self.assertNotIn("na|gold|7d|top|Aatrox", history["series"])
        self.assertEqual(
            history["series"]["na|gold|7d|middle|Ahri"][0]["mastery_gap_pct"],
            12.4,
        )

    def test_duplicate_existing_dates_are_normalized(self) -> None:
        history = new_history()
        history["series"] = {
            "na|gold|7d|top|Aatrox": [
                {
                    "date": "2026-08-01",
                    "delta": 4.2,
                    "win_rate": 51.5,
                    "mastery_gap_pct": 8.1,
                },
                {
                    "date": "2026-08-01",
                    "delta": 4.4,
                    "win_rate": 51.7,
                    "mastery_gap_pct": 8.3,
                },
            ]
        }
        write_dataset(self.root)

        history = merge_fixture(history, self.root, date(2026, 8, 2))

        observations = history["series"]["na|gold|7d|top|Aatrox"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["mastery_gap_pct"], 8.3)

    def test_retention_trims_to_30_utc_dates(self) -> None:
        first_day = date(2026, 7, 1)
        history = new_history()
        for offset in range(31):
            write_dataset(self.root, top=[champion("Aatrox", mastery_gap_pct=float(offset))])
            history = merge_fixture(history, self.root, first_day + timedelta(days=offset))

        observations = history["series"]["na|gold|7d|top|Aatrox"]
        self.assertEqual(len(observations), 30)
        self.assertEqual(observations[0]["date"], "2026-07-02")
        self.assertEqual(observations[-1]["date"], "2026-07-31")

    def test_missing_or_null_mastery_gap_is_skipped(self) -> None:
        missing = champion("Missing")
        missing.pop("mastery_gap_pct")
        write_dataset(
            self.root,
            top=[missing, champion("Null", mastery_gap_pct=None), champion("Valid")],
        )

        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))

        self.assertEqual(list(history["series"]), ["na|gold|7d|top|Valid"])

        write_dataset(self.root, top=[champion("Valid", mastery_gap_pct=None)])
        history = merge_fixture(history, self.root, date(2026, 8, 2))
        self.assertEqual(
            [item["date"] for item in history["series"]["na|gold|7d|top|Valid"]],
            ["2026-08-01"],
        )

    def test_same_champion_in_two_contexts_remains_separate(self) -> None:
        write_dataset(
            self.root,
            top=[champion("Aatrox", mastery_gap_pct=8.1)],
            middle=[champion("Aatrox", mastery_gap_pct=12.4)],
        )

        history = merge_fixture(new_history(), self.root, date(2026, 8, 1))

        self.assertEqual(
            set(history["series"]),
            {"na|gold|7d|top|Aatrox", "na|gold|7d|middle|Aatrox"},
        )

    def test_malformed_or_unsupported_schema_is_rejected(self) -> None:
        history_path = self.root / "difficulty-history.json"
        unsupported = new_history()
        unsupported["schema_version"] = 99
        history_path.write_text(json.dumps(unsupported), encoding="utf-8")

        with self.assertRaisesRegex(HistoryValidationError, "unsupported history schema_version"):
            load_history(history_path)

    def test_partial_matrix_is_rejected_before_history_write(self) -> None:
        history_path = self.root / "difficulty-history.json"
        original = new_history()
        write_history(history_path, original)
        original_payload = history_path.read_text(encoding="utf-8")
        write_dataset(self.root, top=[champion("Aatrox")], partial=True)

        with self.assertRaisesRegex(HistoryValidationError, "is partial"):
            merge_fixture(load_history(history_path), self.root, date(2026, 8, 1))

        self.assertEqual(history_path.read_text(encoding="utf-8"), original_payload)

    def test_serialization_is_deterministic(self) -> None:
        write_dataset(
            self.root,
            top=[champion("Zed")],
            middle=[champion("Aatrox")],
        )

        first = merge_fixture(new_history(), self.root, date(2026, 8, 1))
        second = merge_fixture(new_history(), self.root, date(2026, 8, 1))

        self.assertEqual(serialize_history(first), serialize_history(second))
        self.assertEqual(list(first["series"]), sorted(first["series"]))


if __name__ == "__main__":
    unittest.main()

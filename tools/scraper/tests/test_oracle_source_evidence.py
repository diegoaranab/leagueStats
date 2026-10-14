"""Offline audit of the frozen Phase 1B evidence, not a source adapter."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loltee_scraper.oracle_download import (
    REQUIRED_COLUMNS,
    CsvValidationError,
    validate_oracle_csv,
)


EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "docs/bet-ai/phase-1b"
NOW = datetime(2026, 10, 14, 9, tzinfo=timezone.utc)


class OracleSourceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = json.loads((EVIDENCE_DIR / "source-evidence.json").read_text())
        cls.baseline = json.loads((EVIDENCE_DIR / "baseline-statistics.json").read_text())
        cls.run_evidence = json.loads(
            (EVIDENCE_DIR / "run-38537687360.metadata.json").read_text()
        )

    def test_green_run_is_historical_and_does_not_authorize_bet_ai(self) -> None:
        metadata = self.run_evidence["metadata"]
        self.assertEqual(self.run_evidence["provenance"]["job_conclusion"], "success")
        self.assertEqual(metadata["state"], "STALE")
        self.assertEqual(metadata["source"], "snapshot")
        self.assertFalse(metadata["is_recent_for_bet_ai"])
        self.assertFalse(metadata["cache_updated"])
        attempts = metadata["attempts"]
        for source in ("google-drive-direct", "google-drive-alternate", "gdown"):
            rejected = [a for a in attempts if a["source"] == source]
            self.assertEqual([a["attempt"] for a in rejected], [1, 2])
            self.assertTrue(all(a["outcome"] == "rejected" for a in rejected))

    def test_baseline_reconciles_with_log_and_all_league_counts(self) -> None:
        baseline = self.baseline
        metadata = self.run_evidence["metadata"]
        for field in ("sha256", "size_bytes", "last_match_at"):
            self.assertEqual(baseline["provenance"][field], metadata[field])
        leagues = baseline["leagues"]
        self.assertEqual(len(leagues), 29)
        self.assertEqual(sum(v["rows"] for v in leagues.values()), metadata["row_count"])
        self.assertEqual(sum(v["games"] for v in leagues.values()), metadata["game_count"])
        self.assertEqual(sum(baseline["completeness"].values()), metadata["row_count"])
        self.assertEqual(baseline["rows_per_game"], {"12": metadata["game_count"]})
        self.assertEqual(baseline["duplicate_game_participant_keys"], 0)
        columns = baseline["columns"]
        self.assertEqual(len(columns), baseline["column_count"])
        self.assertEqual(len(columns), len(set(columns)))
        self.assertTrue(REQUIRED_COLUMNS <= set(columns))
        self.assertTrue({"gameid", "playerid", "teamid", "league"} <= set(columns))
        self.assertGreater(baseline["empty_ids"]["playerid"]["player_rows"], 0)
        self.assertGreater(baseline["empty_ids"]["teamid"]["player_rows"], 0)

    def test_no_go_has_unsatisfied_gates_for_every_candidate(self) -> None:
        self.assertEqual(self.evidence["decision"], "NO-GO")
        required = set(self.evidence["freshness_contract"]["required_gates"])
        self.assertEqual(required, {
            "machine_access", "authorized_use", "current_coverage", "csv_compatibility",
        })
        for source in self.evidence["sources"]:
            with self.subTest(source=source["id"]):
                self.assertEqual(set(source["gates"]), required)
                self.assertFalse(all(v is True for v in source["gates"].values()))
                self.assertNotIn(source["state"], {"FRESH", "CACHED"})
                if source["source_status"] == "UNAVAILABLE":
                    self.assertEqual(source["state"], "FAILED")
                    self.assertIsNone(source["last_match_at"])
                    self.assertIsNone(source["downloaded_at"])
        snapshot = next(s for s in self.evidence["sources"]
                        if s["id"] == "historical_repository_snapshot")
        self.assertEqual(snapshot["source_status"], "HISTORICAL")
        self.assertFalse(snapshot["gates"]["current_coverage"])

    def test_api_block_is_not_a_verified_schema_or_dataset(self) -> None:
        probes = {p["id"]: p for p in self.evidence["probes"]}
        for key in ("api_root", "api_match_data", "api_robots"):
            probe = probes[key]
            self.assertEqual(probe["status"], 403)
            self.assertIn("text/html", probe["headers"]["content-type"])
            self.assertFalse(probe["dataset_downloaded"])
            self.assertEqual(probe["attempts"], 1)
            self.assertRegex(probe["body_sha256"], r"^[0-9a-f]{64}$")
        api = next(s for s in self.evidence["sources"] if s["id"] == "official_site_api")
        self.assertIsNone(api["gates"]["csv_compatibility"])
        self.assertIsNone(api["gates"]["current_coverage"])
        self.assertIsNone(api["gates"]["authorized_use"])

    def test_unknown_upstream_dates_are_not_inferred_from_other_clocks(self) -> None:
        contract = self.evidence["freshness_contract"]
        self.assertFalse(contract["implemented"])
        self.assertFalse(contract["match_age_alone_proves_stale"])
        self.assertFalse(contract["new_download_alone_proves_fresh"])
        self.assertFalse(contract["unknown_upstream_time_is_fresh"])
        for source in self.evidence["sources"]:
            self.assertIsNone(source["upstream_changed_at"])
        self.assertIsNone(self.baseline["provenance"]["upstream_changed_at"])
        metadata = self.run_evidence["metadata"]
        parse = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
        age = (parse(metadata["selected_at"]) - parse(metadata["last_match_at"])).total_seconds()
        self.assertEqual(int(age), metadata["data_age_seconds"])
        self.assertEqual(metadata["download_age_seconds"], 0)

    def test_csv_validity_is_independent_of_a_48_hour_gap_without_games(self) -> None:
        # Synthetic CSV, not an API sample. Validation must not infer source age.
        match_at = NOW - timedelta(hours=48)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=sorted(REQUIRED_COLUMNS))
                writer.writeheader()
                for participant in range(1, 13):
                    writer.writerow({
                        "gameid": "synthetic-game", "datacompleteness": "complete",
                        "league": "synthetic-league", "year": "2026",
                        "date": match_at.isoformat(), "patch": "16.20",
                        "participantid": str(participant),
                        "side": "Blue" if participant <= 6 else "Red",
                        "position": ("top", "jng", "mid", "bot", "sup", "team")[
                            (participant - 1) % 6],
                        "champion": "synthetic-champion", "result": "1",
                    })
            report = validate_oracle_csv(path, not_after=NOW, min_bytes=1)
            self.assertEqual(report.game_count, 1)
            self.assertEqual(report.valid_record_count, 12)
            self.assertEqual(report.last_match_at, match_at.isoformat().replace("+00:00", "Z"))

    def test_cloudflare_html_is_rejected_as_csv(self) -> None:
        # Minimal synthetic reproduction of the observed HTML block signature.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked.csv"
            path.write_text('<!DOCTYPE html><html><title>Attention Required!</title></html>')
            with self.assertRaisesRegex(CsvValidationError, "HTML"):
                validate_oracle_csv(path, not_after=NOW, min_bytes=1)


if __name__ == "__main__":
    unittest.main()

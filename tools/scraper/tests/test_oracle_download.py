from __future__ import annotations

import csv
import json
import tempfile
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import loltee_scraper
loltee_scraper.__path__.insert(0, str(Path(__file__).resolve().parents[1] / "src/loltee_scraper"))

from loltee_scraper.oracle_download import (
    DownloadError,
    DownloadState,
    OracleDownloader,
    is_production_current,
)


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
REQUIRED_FIELDS = [
    "gameid",
    "datacompleteness",
    "league",
    "year",
    "date",
    "patch",
    "participantid",
    "side",
    "position",
    "champion",
    "result",
    "ban1",
    "ban2",
    "ban3",
    "ban4",
    "ban5",
]


def write_csv(path: Path, *, match_at: datetime = NOW, games: int = 2) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        for game in range(games):
            gameid = f"GAME-{game}"
            for participant in range(1, 11):
                writer.writerow(
                    {
                        "gameid": gameid,
                        "datacompleteness": "complete",
                        "league": "LCS",
                        "year": "2026",
                        "date": match_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "patch": "16.20",
                        "participantid": str(participant),
                        "side": "Blue" if participant <= 5 else "Red",
                        "position": ("top", "jng", "mid", "bot", "sup")[
                            (participant - 1) % 5
                        ],
                        "champion": f"Champion {participant}",
                        "result": "1" if participant <= 5 else "0",
                        "ban1": "A",
                        "ban2": "B",
                        "ban3": "C",
                        "ban4": "D",
                        "ban5": "E",
                    }
                )
            for side in ("Blue", "Red"):
                writer.writerow(
                    {
                        "gameid": gameid,
                        "datacompleteness": "complete",
                        "league": "LCS",
                        "year": "2026",
                        "date": match_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "patch": "16.20",
                        "side": side,
                        "position": "team",
                        "result": "1" if side == "Blue" else "0",
                        "ban1": "A",
                        "ban2": "B",
                        "ban3": "C",
                        "ban4": "D",
                        "ban5": "E",
                    }
                )


def replace_row_date(path: Path, *, row_index: int, match_at: datetime) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames
    if fieldnames is None:
        raise AssertionError("test CSV has no header")
    rows[row_index]["date"] = match_at.strftime("%Y-%m-%d %H:%M:%S")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class OracleDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.csv = self.root / "valid.csv"
        write_csv(self.csv, match_at=NOW - timedelta(hours=25))
        self.output = self.root / "output.csv"
        self.cache = self.root / "cache.csv"
        self.metadata = self.root / "metadata.json"

    def resolve(self, fetch, now=NOW):
        downloader = OracleDownloader(attempts=1, min_bytes=1, cache_max_age_hours=48, now=lambda: now)
        with patch("loltee_scraper.oracle_download.download_authenticated", side_effect=fetch):
            return downloader.resolve(file_id="official-id", output_path=self.output,
                                      metadata_path=self.metadata, cache_path=self.cache)

    def live(self, file_id, path, **kwargs):
        self.assertEqual(file_id, "official-id")
        path.write_bytes(self.csv.read_bytes())
        return {"md5_verified": True}

    def failed(self, *args, **kwargs):
        raise RuntimeError("synthetic-client-secret synthetic-access-token")

    def test_fresh_and_old_match(self):
        result = self.resolve(self.live)
        self.assertEqual((result.state, result.source), (DownloadState.FRESH, "google-drive-api-oauth"))
        self.assertTrue(result.cache_updated and result.checksum_verified and result.content_changed)
        self.assertEqual(result.download_age_seconds, 0)
        self.assertEqual(result.data_age_seconds, 25 * 3600)
        self.assertTrue(is_production_current(result))
        self.assertEqual(self.cache.read_bytes(), self.csv.read_bytes())
        self.assertFalse(self.resolve(self.live).content_changed)

    def test_failure_uses_valid_cache_without_renewing_age_or_leaking_secrets(self):
        first = self.resolve(self.live)
        cache_meta = self.cache.with_suffix(".csv.metadata.json")
        before = cache_meta.read_bytes()
        result = self.resolve(self.failed, NOW + timedelta(hours=12))
        self.assertEqual((result.state, result.source), (DownloadState.CACHED, "cache"))
        self.assertEqual(result.downloaded_at, first.downloaded_at)
        self.assertEqual(result.download_age_seconds, 12 * 3600)
        self.assertFalse(result.cache_updated)
        self.assertEqual(cache_meta.read_bytes(), before)
        self.assertNotIn("synthetic", json.dumps(result.to_dict()))
        self.assertNotIn("synthetic", self.metadata.read_text())

    def test_expired_corrupt_and_future_cache_fail_closed(self):
        for mode in ("expired", "corrupt", "future", "missing_checksum"):
            with self.subTest(mode=mode):
                self.resolve(self.live)
                meta_path = self.cache.with_suffix(".csv.metadata.json")
                meta = json.loads(meta_path.read_text())
                if mode == "expired": meta["downloaded_at"] = "2026-10-12T11:59:59Z"
                if mode == "future": meta["downloaded_at"] = "2026-10-14T12:00:01Z"
                if mode == "missing_checksum": meta.pop("sha256")
                meta_path.write_text(json.dumps(meta))
                if mode == "corrupt": self.cache.write_bytes(self.cache.read_bytes() + b"x")
                result = self.resolve(self.failed)
                self.assertEqual(result.state, DownloadState.FAILED)
                self.assertFalse(is_production_current(result))

    def test_malformed_prior_cache_metadata_does_not_block_authenticated_live(self):
        metadata_path = self.cache.with_suffix(".csv.metadata.json")
        malformed_values = {
            "non_object": b"[]",
            "invalid_json": b"{not json",
            "invalid_utf8": b"\xff\xfe",
        }
        for mode, contents in malformed_values.items():
            with self.subTest(mode=mode):
                self.cache.write_bytes(self.csv.read_bytes())
                metadata_path.write_bytes(contents)
                result = self.resolve(self.live)
                self.assertEqual(
                    (result.state, result.source),
                    (DownloadState.FRESH, "google-drive-api-oauth"),
                )

    def test_malformed_cache_metadata_is_rejected_as_fallback(self):
        self.cache.write_bytes(self.csv.read_bytes())
        metadata_path = self.cache.with_suffix(".csv.metadata.json")
        metadata_path.write_text("[]", encoding="utf-8")

        result = self.resolve(self.failed)

        self.assertEqual(result.state, DownloadState.FAILED)
        self.assertFalse(is_production_current(result))

    def test_invalid_live_preserves_good_output_and_cache(self):
        self.resolve(self.live)
        previous = self.output.read_bytes()
        def invalid(file_id, path, **kwargs):
            path.write_bytes(b"invalid")
        result = self.resolve(invalid)
        self.assertEqual(result.state, DownloadState.CACHED)
        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(self.cache.read_bytes(), previous)

    def test_no_obsolete_source_or_cli(self):
        source = Path(__file__).resolve().parents[1] / "src/loltee_scraper/oracle_download.py"
        text = source.read_text()
        for obsolete in ("drive.google.com/uc", "drive.usercontent.google.com", "gdown", "snapshot"):
            self.assertNotIn(obsolete, text)


if __name__ == "__main__":
    unittest.main()

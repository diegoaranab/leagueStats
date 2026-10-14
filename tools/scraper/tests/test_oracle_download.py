from __future__ import annotations

import csv
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loltee_scraper.oracle_download import DownloadState, OracleDownloader


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


class FakeSources:
    def __init__(self) -> None:
        self.http_responses: list[bytes | Path | Exception] = []
        self.gdown_responses: list[bytes | Path | Exception] = []
        self.http_calls: list[str] = []
        self.gdown_calls: list[str] = []

    @staticmethod
    def _respond(response: bytes | Path | Exception, destination: Path) -> None:
        if isinstance(response, Exception):
            raise response
        if isinstance(response, Path):
            destination.write_bytes(response.read_bytes())
        else:
            destination.write_bytes(response)

    def http(self, url: str, destination: Path, timeout: float, max_bytes: int) -> None:
        del timeout, max_bytes
        self.http_calls.append(url)
        self._respond(self.http_responses.pop(0), destination)

    def gdown(self, url: str, destination: Path, timeout: float, max_bytes: int) -> None:
        del timeout, max_bytes
        self.gdown_calls.append(url)
        self._respond(self.gdown_responses.pop(0), destination)


class OracleDownloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.valid_csv = self.root / "valid.csv"
        write_csv(self.valid_csv, match_at=NOW - timedelta(hours=2))
        self.sources = FakeSources()
        self.sleeps: list[float] = []

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def downloader(self, **overrides: object) -> OracleDownloader:
        options: dict[str, object] = {
            "attempts": 1,
            "backoff_seconds": 0.25,
            "timeout_seconds": 5,
            "min_bytes": 1,
            "min_records": 12,
            "http_fetcher": self.sources.http,
            "gdown_fetcher": self.sources.gdown,
            "sleeper": self.sleeps.append,
            "now": lambda: NOW,
        }
        options.update(overrides)
        return OracleDownloader(**options)  # type: ignore[arg-type]

    def resolve(self, downloader: OracleDownloader, **overrides: object):
        options: dict[str, object] = {
            "file_id": "test-file",
            "output_path": self.root / "output.csv",
            "metadata_path": self.root / "metadata.json",
        }
        options.update(overrides)
        return downloader.resolve(**options)  # type: ignore[arg-type]

    def fail_fresh_sources(self, error: Exception | None = None) -> None:
        failure = error or urllib.error.HTTPError(
            "https://drive.google.com", 403, "quota", {}, None,
        )
        self.sources.http_responses.extend([failure, failure])
        self.sources.gdown_responses.append(failure)

    def test_successful_direct_download_is_validated_and_has_metadata(self) -> None:
        self.sources.http_responses.append(self.valid_csv)

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FRESH)
        self.assertEqual(result.source, "google-drive-direct")
        self.assertTrue(result.is_recent_for_bet_ai)
        self.assertTrue(result.content_changed)
        self.assertEqual(result.row_count, 24)
        self.assertEqual(result.valid_record_count, 24)
        self.assertEqual(result.game_count, 2)
        self.assertEqual(result.data_age_seconds, 7200)
        self.assertEqual(len(result.sha256 or ""), 64)
        self.assertEqual((self.root / "output.csv").read_bytes(), self.valid_csv.read_bytes())
        stored = json.loads((self.root / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["state"], "FRESH")
        self.assertEqual(stored["sha256"], result.sha256)

    def test_html_quota_pages_and_http_errors_fall_through_to_gdown(self) -> None:
        self.sources.http_responses.extend(
            [
                b"<!doctype html><title>Google Drive - Quota exceeded</title>",
                urllib.error.HTTPError("alternate", 429, "quota", {}, None),
            ]
        )
        self.sources.gdown_responses.append(self.valid_csv)

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FRESH)
        self.assertEqual(result.source, "gdown")
        self.assertIn("HTML", result.attempts[0].detail)
        self.assertIn("HTTPError", result.attempts[1].detail)
        self.assertEqual(len(self.sources.http_calls), 2)
        self.assertEqual(len(self.sources.gdown_calls), 1)

    def test_alternate_google_drive_endpoint_can_succeed(self) -> None:
        self.sources.http_responses.extend(
            [ConnectionError("direct endpoint blocked"), self.valid_csv]
        )

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FRESH)
        self.assertEqual(result.source, "google-drive-alternate")
        self.assertIn("drive.usercontent.google.com", self.sources.http_calls[1])
        self.assertEqual(self.sources.gdown_calls, [])

    def test_exhausted_retries_use_exponential_backoff_and_fail(self) -> None:
        failure = TimeoutError("network timeout")
        self.sources.http_responses.extend([failure] * 6)
        self.sources.gdown_responses.extend([failure] * 3)

        result = self.resolve(self.downloader(attempts=3))

        self.assertEqual(result.state, DownloadState.FAILED)
        self.assertEqual(len(result.attempts), 9)
        self.assertEqual(self.sleeps, [0.25, 0.5] * 3)
        self.assertFalse((self.root / "output.csv").exists())
        self.assertEqual(
            json.loads((self.root / "metadata.json").read_text())["state"],
            "FAILED",
        )

    def test_recent_cache_is_used_after_all_downloads_fail(self) -> None:
        cache = self.root / "cache.csv"
        self.sources.http_responses.append(self.valid_csv)
        first = self.resolve(self.downloader(), cache_path=cache)
        self.assertTrue(first.cache_updated)
        first_output = self.root / "output.csv"
        first_output.unlink()
        self.fail_fresh_sources()

        result = self.resolve(self.downloader(), cache_path=cache)

        self.assertEqual(result.state, DownloadState.CACHED)
        self.assertEqual(result.source, "cache")
        self.assertTrue(result.checksum_verified)
        self.assertFalse(result.content_changed)
        self.assertTrue(result.is_recent_for_bet_ai)
        self.assertEqual(first.sha256, result.sha256)

    def test_old_cache_is_explicitly_stale(self) -> None:
        cache = self.root / "cache.csv"
        self.sources.http_responses.append(self.valid_csv)
        self.resolve(self.downloader(), cache_path=cache)
        cache_metadata_path = cache.with_suffix(".csv.metadata.json")
        cache_metadata = json.loads(cache_metadata_path.read_text(encoding="utf-8"))
        cache_metadata["downloaded_at"] = "2026-10-10T12:00:00Z"
        cache_metadata_path.write_text(json.dumps(cache_metadata), encoding="utf-8")
        self.fail_fresh_sources()

        result = self.resolve(
            self.downloader(cache_max_age_hours=24), cache_path=cache,
        )

        self.assertEqual(result.state, DownloadState.STALE)
        self.assertEqual(result.download_age_seconds, 4 * 24 * 3600)
        self.assertFalse(result.is_recent_for_bet_ai)

    def test_corrupt_cache_checksum_is_rejected(self) -> None:
        cache = self.root / "cache.csv"
        self.sources.http_responses.append(self.valid_csv)
        self.resolve(self.downloader(), cache_path=cache)
        cache.write_bytes(cache.read_bytes() + b"\n")
        self.fail_fresh_sources()

        result = self.resolve(self.downloader(), cache_path=cache)

        self.assertEqual(result.state, DownloadState.FAILED)
        cache_attempt = next(item for item in result.attempts if item.source == "cache")
        self.assertIn("checksum", cache_attempt.detail)

    def test_snapshot_follows_corrupt_cache_and_is_marked_stale(self) -> None:
        cache = self.root / "cache.csv"
        cache.write_text("not,csv\n", encoding="utf-8")
        snapshot = self.root / "snapshot.csv"
        write_csv(snapshot, match_at=NOW - timedelta(days=30))
        self.fail_fresh_sources()

        result = self.resolve(
            self.downloader(), cache_path=cache, snapshot_path=snapshot,
        )

        self.assertEqual(result.state, DownloadState.STALE)
        self.assertEqual(result.source, "snapshot")
        self.assertEqual(result.data_age_seconds, 30 * 24 * 3600)
        self.assertFalse(result.is_recent_for_bet_ai)

    def test_fresh_download_with_old_latest_match_is_stale_for_bet_ai(self) -> None:
        stale_download = self.root / "stale.csv"
        write_csv(stale_download, match_at=NOW - timedelta(hours=25))
        self.sources.http_responses.append(stale_download)

        result = self.resolve(
            self.downloader(bet_ai_max_data_age_hours=24),
        )

        self.assertEqual(result.state, DownloadState.STALE)
        self.assertEqual(result.source, "google-drive-direct")
        self.assertFalse(result.is_recent_for_bet_ai)
        self.assertEqual(result.data_age_seconds, 25 * 3600)

    def test_identical_download_is_successful_but_not_updated(self) -> None:
        output = self.root / "output.csv"
        output.write_bytes(self.valid_csv.read_bytes())
        self.sources.http_responses.append(self.valid_csv)

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FRESH)
        self.assertFalse(result.content_changed)

    def test_invalid_download_never_replaces_existing_output(self) -> None:
        output = self.root / "output.csv"
        original = b"previous known-good contents"
        output.write_bytes(original)
        self.sources.http_responses.extend([b"<html>blocked</html>"] * 2)
        self.sources.gdown_responses.append(b"<html>blocked</html>")

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FAILED)
        self.assertEqual(output.read_bytes(), original)

    def test_no_valid_source_reports_failed_with_attempt_details(self) -> None:
        self.fail_fresh_sources(ConnectionError("offline"))

        result = self.resolve(self.downloader())

        self.assertEqual(result.state, DownloadState.FAILED)
        self.assertEqual(result.source, "none")
        self.assertIsNone(result.sha256)
        self.assertEqual(
            [attempt.source for attempt in result.attempts],
            ["google-drive-direct", "google-drive-alternate", "gdown"],
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import io
import json
import tempfile
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_ROOT))
import loltee_scraper
loltee_scraper.__path__.insert(0, str(SOURCE_ROOT / "loltee_scraper"))

from loltee_scraper import oracle_drive_api as drive
from test_oracle_download import write_csv, NOW

CREDS = {"GOOGLE_DRIVE_CLIENT_ID": "synthetic-client-id", "GOOGLE_DRIVE_CLIENT_SECRET": "synthetic-client-secret", "GOOGLE_DRIVE_REFRESH_TOKEN": "synthetic-refresh-token"}
ACCESS = "synthetic-access-token"


class Response(io.BytesIO):
    def __init__(self, data: bytes, headers: dict | None = None):
        super().__init__(data)
        self.headers = headers or {}


class OracleDriveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        csv_path = self.root / "fixture.csv"
        write_csv(csv_path, match_at=NOW.replace(month=1, day=1))
        lines = csv_path.read_bytes().splitlines(keepends=True)
        self.csv = lines[0] + b"".join(lines[1:] * 500)
        self.metadata = {"id": drive.FILE_ID, "name": "oracle.csv", "mimeType": "text/csv", "size": str(len(self.csv)), "md5Checksum": hashlib.md5(self.csv, usedforsecurity=False).hexdigest(), "modifiedTime": "2026-10-14T12:00:00Z", "version": "1"}
        self.output = self.root / "metadata.json"
        self.env = patch.dict("os.environ", CREDS)
        self.env.start()
        self.addCleanup(self.env.stop)

    def execute(self, *, metadata=None, data=None, token=None, max_bytes=drive.MAX_BYTES):
        payload = self.csv if data is None else data
        responses = [Response(json.dumps(token or {"access_token": ACCESS, "token_type": "Bearer"}).encode()), Response(json.dumps(self.metadata if metadata is None else metadata).encode()), Response(payload)]
        with patch("urllib.request.build_opener") as build:
            opener = build.return_value
            opener.open.side_effect = responses
            result = drive.run_diagnostic(self.output, max_bytes=max_bytes)
            return result, opener.open.call_args_list

    def test_success_streams_and_validates_with_authenticated_requests(self):
        result, calls = self.execute()
        self.assertEqual(len(calls), 3)
        token_request = calls[0].args[0]
        self.assertEqual(token_request.full_url, drive.TOKEN_URL)
        self.assertIn(b"grant_type=refresh_token", token_request.data)
        for call in calls[1:]:
            self.assertEqual(call.args[0].get_header("Authorization"), "Bearer " + ACCESS)
            self.assertIn(drive.FILE_ID, call.args[0].full_url)
        self.assertIn("alt=media", calls[2].args[0].full_url)
        self.assertTrue(result["md5_verified"])
        self.assertEqual(result["local_size"], len(self.csv))
        self.assertEqual(result["sha256"], hashlib.sha256(self.csv).hexdigest())
        self.assertGreater(result["row_count"], 12)
        self.assertEqual(result["state"], "VALIDATED")
        self.assertLess(result["last_match_at"], NOW.isoformat())
        self.assertNotIn("data_age_seconds", result)
        self.assertNotIn("data_age_seconds", json.loads(self.output.read_text()))
        serialized = self.output.read_text()
        for secret in (*CREDS.values(), ACCESS, "Bearer " + ACCESS):
            self.assertNotIn(secret, serialized)

    def test_authentication_failure_is_sanitized(self):
        with patch("urllib.request.build_opener") as build:
            build.return_value.open.side_effect = RuntimeError("synthetic-client-secret synthetic-refresh-token")
            with self.assertRaises(drive.DiagnosticError) as error:
                drive.run_diagnostic(self.output)
        self.assertNotIn("synthetic", str(error.exception))
        self.assertFalse(self.output.exists())

    def test_metadata_mismatch(self):
        with self.assertRaisesRegex(drive.DiagnosticError, "ID mismatch"):
            self.execute(metadata={**self.metadata, "id": "other"})
        self.assertFalse(self.output.exists())

    def test_md5_mismatch(self):
        with self.assertRaisesRegex(drive.DiagnosticError, "MD5 mismatch"):
            self.execute(metadata={**self.metadata, "md5Checksum": "0" * 32})
        self.assertFalse(self.output.exists())

    def test_invalid_csv(self):
        invalid = b"x" * 1_000_000
        with self.assertRaises(drive.DiagnosticError):
            self.execute(metadata={**self.metadata, "size": str(len(invalid)), "md5Checksum": hashlib.md5(invalid, usedforsecurity=False).hexdigest()}, data=invalid)
        self.assertFalse(self.output.exists())

    def test_oversized_stream(self):
        with self.assertRaisesRegex(drive.DiagnosticError, "exceeds download limit"):
            self.execute(metadata={**self.metadata, "size": "99"}, max_bytes=100)
        self.assertFalse(self.output.exists())

    def test_size_mismatch_and_workspace_type(self):
        for metadata in ({**self.metadata, "size": "1"}, {**self.metadata, "mimeType": "application/vnd.google-apps.document"}):
            with self.subTest(metadata=metadata), self.assertRaises(drive.DiagnosticError):
                self.execute(metadata=metadata)

    def test_metadata_containing_secret_rejected(self):
        with self.assertRaisesRegex(drive.DiagnosticError, "Unsafe"):
            self.execute(metadata={**self.metadata, "name": ACCESS})
        self.assertFalse(self.output.exists())

    def test_production_resolver_runs_authenticated_integrity_and_csv_validation(self):
        from loltee_scraper.oracle_download import OracleDownloader, DownloadState
        downloader = OracleDownloader(attempts=1, min_bytes=1, cache_max_age_hours=48, now=lambda: NOW)
        output, cache, meta = (self.root / name for name in ("output.csv", "cache.csv", "result.json"))
        def run(metadata, data):
            responses = [Response(json.dumps({"access_token": ACCESS, "token_type": "Bearer"}).encode()),
                         Response(json.dumps(metadata).encode()), Response(data)]
            with patch("urllib.request.build_opener") as build:
                build.return_value.open.side_effect = responses
                result = downloader.resolve(file_id=drive.FILE_ID, output_path=output, metadata_path=meta, cache_path=cache)
                calls = build.return_value.open.call_args_list
            return result, calls
        result, calls = run(self.metadata, self.csv)
        self.assertEqual((result.state, result.source), (DownloadState.FRESH, "google-drive-api-oauth"))
        self.assertTrue(result.cache_updated and result.checksum_verified)
        self.assertTrue(all(drive.FILE_ID in call.args[0].full_url for call in calls[1:]))
        self.assertGreater(result.data_age_seconds, 24 * 3600)
        for secret in (*CREDS.values(), ACCESS, "Bearer " + ACCESS):
            self.assertNotIn(secret, meta.read_text())
        original = output.read_bytes()
        for bad in ({**self.metadata, "size": "1"}, {**self.metadata, "md5Checksum": "0" * 32}):
            result, _ = run(bad, self.csv)
            self.assertEqual(result.state, DownloadState.CACHED)
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(cache.read_bytes(), original)

    def test_diagnostic_metadata_contains_only_leaguestats_observations(self):
        result, _ = self.execute()
        self.assertEqual(result["file_id"], drive.FILE_ID)
        self.assertIn("last_match_at", result)
        self.assertEqual(set(result) - {"state", "source", "file_id", "file_name", "mime_type", "drive_size", "local_size", "drive_md5_checksum", "md5_verified", "drive_modified_time", "drive_version", "downloaded_at", "sha256", "row_count", "valid_record_count", "game_count", "last_match_at"}, set())


if __name__ == "__main__":
    unittest.main()

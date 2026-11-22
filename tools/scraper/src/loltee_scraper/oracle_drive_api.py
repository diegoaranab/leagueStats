from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from loltee_scraper.oracle_download import validate_oracle_csv

FILE_ID = "1hnpbrUpBMS1TZI7IovfpKeZfWJH1Aptm"
TOKEN_URL = "https://oauth2.googleapis.com/token"
FILE_URL = f"https://www.googleapis.com/drive/v3/files/{FILE_ID}"
MAX_BYTES = 1_000_000_000


class DiagnosticError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _json_response(opener, request, timeout):
    with opener.open(request, timeout=timeout) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise DiagnosticError("API response exceeds the metadata limit")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise DiagnosticError("Invalid API response")
    return value


def run_diagnostic(metadata_path: Path, *, max_bytes: int = MAX_BYTES, timeout: float = 180) -> dict:
    # Remove any previous result so a failed run cannot expose stale success.
    metadata_path.unlink(missing_ok=True)
    # Only fixed endpoints and the official object are used; redirects fail closed.
    credentials = [os.environ.get(name, "") for name in (
        "GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN"
    )]
    if not all(credentials):
        raise DiagnosticError("Missing Google Drive OAuth credentials")
    opener = urllib.request.build_opener(NoRedirect())
    form = urllib.parse.urlencode(dict(zip(
        ("client_id", "client_secret", "refresh_token", "grant_type"),
        (*credentials, "refresh_token"),
    ))).encode()
    try:
        token = _json_response(opener, urllib.request.Request(TOKEN_URL, data=form), timeout)
        access_token = token.get("access_token")
        if (not isinstance(access_token, str) or not access_token
                or not isinstance(token.get("token_type"), str)
                or token["token_type"].lower() != "bearer"
                or not re.fullmatch(r"[A-Za-z0-9._~+/=-]+", access_token)):
            raise DiagnosticError("Invalid OAuth token response")
        authorization = f"Bearer {access_token}"
        headers = {"Authorization": authorization}
        fields = "id,name,mimeType,size,md5Checksum,modifiedTime,version"
        request = urllib.request.Request(FILE_URL + "?" + urllib.parse.urlencode({"fields": fields}), headers=headers)
        metadata = _json_response(opener, request, timeout)
        if metadata.get("id") != FILE_ID:
            raise DiagnosticError("Drive file ID mismatch")
        mime = metadata.get("mimeType")
        if not isinstance(mime, str) or not mime or mime.startswith("application/vnd.google-apps."):
            raise DiagnosticError("Unsupported Drive MIME type")
        size = metadata.get("size")
        if size is not None:
            if not isinstance(size, str) or not size.isascii() or not size.isdigit():
                raise DiagnosticError("Invalid Drive size")
            size = int(size)
            if size > max_bytes:
                raise DiagnosticError("Drive file exceeds download limit")
        expected_md5 = metadata.get("md5Checksum")
        if expected_md5 is not None and (not isinstance(expected_md5, str) or not re.fullmatch(r"[a-fA-F0-9]{32}", expected_md5)):
            raise DiagnosticError("Invalid Drive MD5 checksum")
        with tempfile.TemporaryDirectory(prefix="oracle-drive-") as directory:
            path = Path(directory) / "download.csv"
            request = urllib.request.Request(FILE_URL + "?alt=media", headers=headers)
            digest = hashlib.md5(usedforsecurity=False)
            total = 0
            with opener.open(request, timeout=timeout) as response, path.open("wb") as output:
                length = response.headers.get("Content-Length")
                if length is not None and (not length.isascii() or not length.isdigit() or int(length) > max_bytes):
                    raise DiagnosticError("Invalid or oversized media response")
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise DiagnosticError("Media response exceeds download limit")
                    digest.update(chunk)
                    output.write(chunk)
            if size is not None and size != total:
                raise DiagnosticError("Drive size mismatch")
            if expected_md5 is not None and digest.hexdigest() != expected_md5.lower():
                raise DiagnosticError("Drive MD5 mismatch")
            now = datetime.now(timezone.utc)
            report = validate_oracle_csv(path, not_after=now, expected_year=2026)
            result = {
                "state": "VALIDATED", "source": "google-drive-api-oauth", "file_id": FILE_ID,
                "file_name": metadata.get("name"), "mime_type": mime, "drive_size": size,
                "local_size": total, "drive_md5_checksum": expected_md5,
                "md5_verified": expected_md5 is not None,
                "drive_modified_time": metadata.get("modifiedTime"), "drive_version": metadata.get("version"),
                "downloaded_at": now.isoformat().replace("+00:00", "Z"), "sha256": report.sha256,
                "row_count": report.row_count, "valid_record_count": report.valid_record_count,
                "game_count": report.game_count, "last_match_at": report.last_match_at,
            }
            serialized = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
            if any(
                secret in serialized or json.dumps(secret, ensure_ascii=False)[1:-1] in serialized
                for secret in (*credentials, access_token, authorization)
            ):
                raise DiagnosticError("Unsafe diagnostic metadata")
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(serialized, encoding="utf-8")
            return result
    except DiagnosticError:
        raise
    except Exception:
        # Never propagate remote bodies, HTTP headers, credentials, or exception chains.
        raise DiagnosticError("Authenticated Drive diagnostic failed") from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the official Oracle file through the Drive API.")
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        run_diagnostic(args.metadata)
    except DiagnosticError as error:
        print(f"Oracle Drive diagnostic failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import hashlib
import http.cookiejar
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Callable, Sequence

try:
    import resource
except ImportError:  # pragma: no cover - Windows uses the polling guard below.
    resource = None  # type: ignore[assignment]


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)
REQUIRED_COLUMNS = frozenset(
    {
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
    }
)
VALID_POSITIONS = frozenset({"top", "jng", "mid", "bot", "sup", "team"})
PLAYER_POSITIONS = VALID_POSITIONS - {"team"}
HTML_MARKERS = (
    b"<!doctype html",
    b"<html",
    b"google drive - quota exceeded",
    b"download quota is exceeded",
    b"too many users have viewed or downloaded",
)


class DownloadState(StrEnum):
    FRESH = "FRESH"
    CACHED = "CACHED"
    STALE = "STALE"
    FAILED = "FAILED"


class DownloadError(RuntimeError):
    pass


class CsvValidationError(DownloadError):
    pass


@dataclass(frozen=True, slots=True)
class ValidationReport:
    sha256: str
    size_bytes: int
    row_count: int
    valid_record_count: int
    game_count: int
    last_match_at: str


@dataclass(frozen=True, slots=True)
class AttemptReport:
    source: str
    attempt: int
    outcome: str
    detail: str


@dataclass(frozen=True, slots=True)
class DownloadResult:
    state: DownloadState
    source: str
    output_path: str
    metadata_path: str
    downloaded_at: str | None
    selected_at: str
    last_match_at: str | None
    download_age_seconds: int | None
    data_age_seconds: int | None
    sha256: str | None
    size_bytes: int | None
    row_count: int | None
    valid_record_count: int | None
    game_count: int | None
    checksum_verified: bool
    content_changed: bool | None
    cache_updated: bool
    bet_ai_max_data_age_hours: float
    is_recent_for_bet_ai: bool
    attempts: tuple[AttemptReport, ...]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["state"] = self.state.value
        return payload


HttpFetcher = Callable[[str, Path, float, int], None]
GdownFetcher = Callable[[str, Path, float, int], None]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(now: datetime, value: datetime) -> int:
    if value > now:
        raise CsvValidationError(
            f"timestamp {_isoformat(value)} is later than selection time {_isoformat(now)}"
        )
    return int((now - value).total_seconds())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent,
    )
    os.close(descriptor)
    temp_path = Path(raw_temp_path)
    try:
        shutil.copyfile(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)


def validate_oracle_csv(
    path: Path,
    *,
    not_after: datetime | None = None,
    expected_year: int = 2026,
    min_bytes: int = 1_000_000,
    max_bytes: int = 1_000_000_000,
    min_records: int = 12,
    min_valid_ratio: float = 0.95,
) -> ValidationReport:
    not_after = (not_after or _utc_now()).astimezone(timezone.utc)
    try:
        size_bytes = path.stat().st_size
    except OSError as error:
        raise CsvValidationError(f"CSV is unavailable: {error}") from error

    if size_bytes > max_bytes:
        raise CsvValidationError(
            f"CSV exceeds the {max_bytes}-byte maximum ({size_bytes} bytes)"
        )

    with path.open("rb") as handle:
        prefix = handle.read(4096).lstrip().lower()
    if b"\x00" in prefix:
        raise CsvValidationError("response contains binary NUL bytes")
    if any(marker in prefix for marker in HTML_MARKERS):
        raise CsvValidationError("response is HTML or a Google Drive quota page, not CSV")
    if size_bytes < min_bytes:
        raise CsvValidationError(
            f"CSV is smaller than the {min_bytes}-byte minimum ({size_bytes} bytes)"
        )

    row_count = 0
    valid_record_count = 0
    games: set[str] = set()
    last_match: datetime | None = None

    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            columns = set(reader.fieldnames or ())
            missing = sorted(REQUIRED_COLUMNS - columns)
            if missing:
                raise CsvValidationError(
                    f"CSV is missing required columns: {', '.join(missing)}"
                )

            for row in reader:
                row_count += 1
                position = (row.get("position") or "").strip().lower()
                gameid = (row.get("gameid") or "").strip()
                league = (row.get("league") or "").strip()
                side = (row.get("side") or "").strip().lower()
                patch = (row.get("patch") or "").strip()
                try:
                    row_year = int((row.get("year") or "").strip())
                    match_at = _parse_datetime(row.get("date") or "")
                except (TypeError, ValueError):
                    continue
                if match_at > not_after:
                    raise CsvValidationError(
                        "CSV contains a future match timestamp: "
                        f"{_isoformat(match_at)} > {_isoformat(not_after)}"
                    )

                player_fields_valid = True
                if position in PLAYER_POSITIONS:
                    player_fields_valid = bool(
                        (row.get("participantid") or "").strip()
                        and (row.get("champion") or "").strip()
                        and (row.get("result") or "").strip() in {"0", "1"}
                    )

                if not (
                    gameid
                    and league
                    and side in {"blue", "red"}
                    and patch
                    and position in VALID_POSITIONS
                    and row_year == expected_year
                    and match_at.year == expected_year
                    and player_fields_valid
                ):
                    continue

                valid_record_count += 1
                games.add(gameid)
                if last_match is None or match_at > last_match:
                    last_match = match_at
    except (csv.Error, UnicodeDecodeError) as error:
        raise CsvValidationError(f"response is not a readable CSV: {error}") from error

    if row_count < min_records:
        raise CsvValidationError(
            f"CSV has fewer than {min_records} records ({row_count})"
        )
    required_valid = max(min_records, math.ceil(row_count * min_valid_ratio))
    if valid_record_count < required_valid:
        raise CsvValidationError(
            "CSV does not contain enough valid 2026 Oracle records "
            f"({valid_record_count}/{row_count}; required {required_valid})"
        )
    if not games or last_match is None:
        raise CsvValidationError("CSV has no valid games or match timestamps")

    return ValidationReport(
        sha256=_sha256(path),
        size_bytes=size_bytes,
        row_count=row_count,
        valid_record_count=valid_record_count,
        game_count=len(games),
        last_match_at=_isoformat(last_match),
    )


class OracleDownloader:
    def __init__(
        self,
        *,
        attempts: int = 3,
        backoff_seconds: float = 2.0,
        timeout_seconds: float = 180.0,
        expected_year: int = 2026,
        min_bytes: int = 1_000_000,
        max_bytes: int = 1_000_000_000,
        min_records: int = 12,
        min_valid_ratio: float = 0.95,
        cache_max_age_hours: float = 168.0,
        bet_ai_max_data_age_hours: float = 24.0,
        http_fetcher: HttpFetcher | None = None,
        gdown_fetcher: GdownFetcher | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds
        self.expected_year = expected_year
        self.min_bytes = min_bytes
        self.max_bytes = max_bytes
        self.min_records = min_records
        self.min_valid_ratio = min_valid_ratio
        self.cache_max_age_seconds = int(cache_max_age_hours * 3600)
        self.bet_ai_max_data_age_hours = bet_ai_max_data_age_hours
        self.bet_ai_max_data_age_seconds = int(bet_ai_max_data_age_hours * 3600)
        self.sleeper = sleeper
        self.now = now
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        self.http_fetcher = http_fetcher or self._download_http
        self.gdown_fetcher = gdown_fetcher or self._download_gdown

    def _download_http(
        self, url: str, destination: Path, timeout: float, max_bytes: int,
    ) -> None:
        request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with self._opener.open(request, timeout=timeout) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                raise DownloadError(
                    f"response Content-Length exceeds {max_bytes} bytes"
                )
            total = 0
            with destination.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise DownloadError(f"response exceeds {max_bytes} bytes")
                    handle.write(chunk)

    def _download_gdown(
        self, url: str, destination: Path, timeout: float, max_bytes: int,
    ) -> None:
        def limit_child_file_size() -> None:
            if resource is None:
                return
            _, hard_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
            enforced_limit = (
                max_bytes
                if hard_limit == resource.RLIM_INFINITY
                else min(max_bytes, hard_limit)
            )
            resource.setrlimit(
                resource.RLIMIT_FSIZE, (enforced_limit, enforced_limit),
            )

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gdown",
                url,
                "--user-agent",
                DEFAULT_USER_AGENT,
                "-O",
                str(destination),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=limit_child_file_size if resource is not None else None,
        )
        deadline = time.monotonic() + timeout
        stdout = ""
        stderr = ""
        while True:
            size_bytes = destination.stat().st_size if destination.exists() else 0
            if size_bytes > max_bytes:
                process.kill()
                stdout, stderr = process.communicate()
                raise DownloadError(
                    f"gdown response exceeds the {max_bytes}-byte maximum"
                )

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                stdout, stderr = process.communicate()
                raise DownloadError(f"gdown exceeded the {timeout}-second timeout")
            try:
                stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue

        size_bytes = destination.stat().st_size if destination.exists() else 0
        if size_bytes > max_bytes or (process.returncode != 0 and size_bytes >= max_bytes):
            raise DownloadError(
                f"gdown response reached the {max_bytes}-byte maximum"
            )
        if process.returncode != 0:
            detail = (stderr or stdout).strip()
            raise DownloadError(f"gdown exited {process.returncode}: {detail[-500:]}")

    def _validate(self, path: Path, *, not_after: datetime) -> ValidationReport:
        return validate_oracle_csv(
            path,
            not_after=not_after,
            expected_year=self.expected_year,
            min_bytes=self.min_bytes,
            max_bytes=self.max_bytes,
            min_records=self.min_records,
            min_valid_ratio=self.min_valid_ratio,
        )

    def _temporary_path(self, parent: Path, name: str) -> Path:
        parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{name}.", suffix=".download", dir=parent,
        )
        os.close(descriptor)
        return Path(raw_path)

    def _try_source(
        self,
        *,
        source: str,
        fetch: Callable[[Path], None],
        temp_parent: Path,
        attempts: list[AttemptReport],
        not_after: datetime,
    ) -> tuple[Path, ValidationReport] | None:
        for attempt in range(1, self.attempts + 1):
            temporary = self._temporary_path(temp_parent, source)
            try:
                fetch(temporary)
                report = self._validate(temporary, not_after=not_after)
                attempts.append(AttemptReport(source, attempt, "accepted", "valid CSV"))
                return temporary, report
            except Exception as error:  # Each source must fail closed and allow fallback.
                attempts.append(
                    AttemptReport(source, attempt, "rejected", f"{type(error).__name__}: {error}")
                )
                temporary.unlink(missing_ok=True)
                if attempt < self.attempts:
                    self.sleeper(self.backoff_seconds * (2 ** (attempt - 1)))
        return None

    def _prior_checksum(self, output: Path, cache: Path | None) -> str | None:
        for candidate in (output, cache):
            if candidate is not None and candidate.is_file():
                try:
                    return _sha256(candidate)
                except OSError:
                    continue
        return None

    def _base_result(
        self,
        *,
        state: DownloadState,
        source: str,
        output: Path,
        metadata: Path,
        downloaded_at: datetime | None,
        selected_at: datetime,
        report: ValidationReport | None,
        checksum_verified: bool,
        content_changed: bool | None,
        cache_updated: bool,
        attempts: list[AttemptReport],
    ) -> DownloadResult:
        last_match = _parse_datetime(report.last_match_at) if report else None
        data_age = _age_seconds(selected_at, last_match) if last_match else None
        download_age = (
            _age_seconds(selected_at, downloaded_at) if downloaded_at else None
        )
        recent = bool(
            report
            and data_age is not None
            and data_age <= self.bet_ai_max_data_age_seconds
            and state in {DownloadState.FRESH, DownloadState.CACHED}
        )
        return DownloadResult(
            state=state,
            source=source,
            output_path=str(output),
            metadata_path=str(metadata),
            downloaded_at=_isoformat(downloaded_at) if downloaded_at else None,
            selected_at=_isoformat(selected_at),
            last_match_at=report.last_match_at if report else None,
            download_age_seconds=download_age,
            data_age_seconds=data_age,
            sha256=report.sha256 if report else None,
            size_bytes=report.size_bytes if report else None,
            row_count=report.row_count if report else None,
            valid_record_count=report.valid_record_count if report else None,
            game_count=report.game_count if report else None,
            checksum_verified=checksum_verified,
            content_changed=content_changed,
            cache_updated=cache_updated,
            bet_ai_max_data_age_hours=self.bet_ai_max_data_age_hours,
            is_recent_for_bet_ai=recent,
            attempts=tuple(attempts),
        )

    def _write_result(self, result: DownloadResult, metadata: Path) -> DownloadResult:
        _atomic_json_write(metadata, result.to_dict())
        return result

    def resolve(
        self,
        *,
        file_id: str,
        output_path: Path,
        metadata_path: Path,
        cache_path: Path | None = None,
        snapshot_path: Path | None = None,
        snapshot_url: str | None = None,
    ) -> DownloadResult:
        selected_at = self.now().astimezone(timezone.utc)
        attempts: list[AttemptReport] = []
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prior_checksum = self._prior_checksum(output_path, cache_path)

        direct_url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm=t"
        alternate_url = (
            "https://drive.usercontent.google.com/download"
            f"?id={file_id}&export=download&confirm=t"
        )
        gdown_url = f"https://drive.google.com/uc?id={file_id}"
        fresh_sources: Sequence[tuple[str, Callable[[Path], None]]] = (
            (
                "google-drive-direct",
                lambda path: self.http_fetcher(
                    direct_url, path, self.timeout_seconds, self.max_bytes,
                ),
            ),
            (
                "google-drive-alternate",
                lambda path: self.http_fetcher(
                    alternate_url, path, self.timeout_seconds, self.max_bytes,
                ),
            ),
            (
                "gdown",
                lambda path: self.gdown_fetcher(
                    gdown_url, path, self.timeout_seconds, self.max_bytes,
                ),
            ),
        )

        for source, fetch in fresh_sources:
            accepted = self._try_source(
                source=source,
                fetch=fetch,
                temp_parent=output_path.parent,
                attempts=attempts,
                not_after=selected_at,
            )
            if accepted is None:
                continue
            temporary, report = accepted
            try:
                os.replace(temporary, output_path)
            finally:
                temporary.unlink(missing_ok=True)
            result = self._base_result(
                state=DownloadState.FRESH,
                source=source,
                output=output_path,
                metadata=metadata_path,
                downloaded_at=selected_at,
                selected_at=selected_at,
                report=report,
                checksum_verified=True,
                content_changed=prior_checksum != report.sha256,
                cache_updated=cache_path is not None,
                attempts=attempts,
            )
            self._write_result(result, metadata_path)
            if cache_path is not None:
                _atomic_copy(output_path, cache_path)
                _atomic_json_write(
                    cache_path.with_suffix(cache_path.suffix + ".metadata.json"),
                    result.to_dict(),
                )
            return result

        if cache_path is not None and cache_path.is_file():
            try:
                report = self._validate(cache_path, not_after=selected_at)
                cache_metadata_path = cache_path.with_suffix(
                    cache_path.suffix + ".metadata.json"
                )
                cache_metadata: dict[str, object] = {}
                if cache_metadata_path.is_file():
                    cache_metadata = json.loads(cache_metadata_path.read_text(encoding="utf-8"))
                expected_checksum = cache_metadata.get("sha256")
                checksum_verified = isinstance(expected_checksum, str)
                if checksum_verified and expected_checksum != report.sha256:
                    raise CsvValidationError(
                        "cache checksum does not match its metadata"
                    )
                downloaded_raw = cache_metadata.get("downloaded_at")
                downloaded_at = (
                    _parse_datetime(downloaded_raw)
                    if isinstance(downloaded_raw, str)
                    else datetime.fromtimestamp(cache_path.stat().st_mtime, timezone.utc)
                )
                for field in ("selected_at", "last_match_at"):
                    value = cache_metadata.get(field)
                    if isinstance(value, str):
                        _age_seconds(selected_at, _parse_datetime(value))
                download_age = _age_seconds(selected_at, downloaded_at)
                cache_is_recent = (
                    checksum_verified
                    and download_age <= self.cache_max_age_seconds
                )
                state = DownloadState.CACHED if cache_is_recent else DownloadState.STALE
                _atomic_copy(cache_path, output_path)
                attempts.append(
                    AttemptReport(
                        "cache",
                        1,
                        "accepted",
                        f"valid cache; age={download_age}s; checksum_verified={checksum_verified}",
                    )
                )
                result = self._base_result(
                    state=state,
                    source="cache",
                    output=output_path,
                    metadata=metadata_path,
                    downloaded_at=downloaded_at,
                    selected_at=selected_at,
                    report=report,
                    checksum_verified=checksum_verified,
                    content_changed=False,
                    cache_updated=False,
                    attempts=attempts,
                )
                return self._write_result(result, metadata_path)
            except Exception as error:
                attempts.append(
                    AttemptReport(
                        "cache", 1, "rejected", f"{type(error).__name__}: {error}"
                    )
                )

        snapshot_fetch: Callable[[Path], None] | None = None
        if snapshot_path is not None:
            snapshot_fetch = lambda path: shutil.copyfile(snapshot_path, path)
        elif snapshot_url:
            snapshot_fetch = lambda path: self.http_fetcher(
                snapshot_url, path, self.timeout_seconds, self.max_bytes,
            )

        if snapshot_fetch is not None:
            accepted = self._try_source(
                source="snapshot",
                fetch=snapshot_fetch,
                temp_parent=output_path.parent,
                attempts=attempts,
                not_after=selected_at,
            )
            if accepted is not None:
                temporary, report = accepted
                try:
                    os.replace(temporary, output_path)
                finally:
                    temporary.unlink(missing_ok=True)
                result = self._base_result(
                    state=DownloadState.STALE,
                    source="snapshot",
                    output=output_path,
                    metadata=metadata_path,
                    downloaded_at=selected_at if snapshot_url else None,
                    selected_at=selected_at,
                    report=report,
                    checksum_verified=True,
                    content_changed=prior_checksum != report.sha256,
                    cache_updated=False,
                    attempts=attempts,
                )
                return self._write_result(result, metadata_path)

        result = self._base_result(
            state=DownloadState.FAILED,
            source="none",
            output=output_path,
            metadata=metadata_path,
            downloaded_at=None,
            selected_at=selected_at,
            report=None,
            checksum_verified=False,
            content_changed=None,
            cache_updated=False,
            attempts=attempts,
        )
        return self._write_result(result, metadata_path)


def _write_github_outputs(result: DownloadResult) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"state={result.state.value}\n")
        handle.write(f"source={result.source}\n")
        handle.write(f"cache_updated={str(result.cache_updated).lower()}\n")
        handle.write(f"content_changed={str(result.content_changed).lower()}\n")
        handle.write(f"downloaded_at={result.downloaded_at or ''}\n")
        handle.write(f"selected_at={result.selected_at}\n")
        handle.write(f"last_match_at={result.last_match_at or ''}\n")
        handle.write(
            f"download_age_seconds={result.download_age_seconds if result.download_age_seconds is not None else ''}\n"
        )
        handle.write(
            f"data_age_seconds={result.data_age_seconds if result.data_age_seconds is not None else ''}\n"
        )
        handle.write(
            f"is_recent_for_bet_ai={str(result.is_recent_for_bet_ai).lower()}\n"
        )


def is_production_current(result: DownloadResult) -> bool:
    """Return whether LeagueStats may publish Teamplay data from this result.

    This policy deliberately uses retrieval/cache age (encoded by state), not
    the age of the newest match. Snapshots remain diagnostic-only.
    """
    return (
        result.state in {DownloadState.FRESH, DownloadState.CACHED}
        and result.source != "snapshot"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reliably download and validate Oracle's Elixir CSV data."
    )
    parser.add_argument("--file-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--cache", type=Path)
    snapshot = parser.add_mutually_exclusive_group()
    snapshot.add_argument("--snapshot-path", type=Path)
    snapshot.add_argument("--snapshot-url")
    parser.add_argument("--expected-year", type=int, default=2026)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--min-bytes", type=int, default=1_000_000)
    parser.add_argument("--max-bytes", type=int, default=1_000_000_000)
    parser.add_argument("--min-records", type=int, default=12)
    parser.add_argument("--cache-max-age-hours", type=float, default=168.0)
    parser.add_argument("--bet-ai-max-data-age-hours", type=float, default=24.0)
    parser.add_argument(
        "--require-production-current",
        action="store_true",
        help=(
            "Fail unless resolution produced a fresh live download or a validated "
            "cache within --cache-max-age-hours. Match age does not affect this gate."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    downloader = OracleDownloader(
        attempts=args.attempts,
        backoff_seconds=args.backoff_seconds,
        timeout_seconds=args.timeout_seconds,
        expected_year=args.expected_year,
        min_bytes=args.min_bytes,
        max_bytes=args.max_bytes,
        min_records=args.min_records,
        cache_max_age_hours=args.cache_max_age_hours,
        bet_ai_max_data_age_hours=args.bet_ai_max_data_age_hours,
    )
    result = downloader.resolve(
        file_id=args.file_id,
        output_path=args.output,
        metadata_path=args.metadata,
        cache_path=args.cache,
        snapshot_path=args.snapshot_path,
        snapshot_url=args.snapshot_url,
    )
    _write_github_outputs(result)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    if args.require_production_current:
        return 0 if is_production_current(result) else 1
    return 1 if result.state is DownloadState.FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())

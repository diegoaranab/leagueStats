from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from .config import SUPPORTED_REGIONS, SUPPORTED_TIERS, SUPPORTED_WINDOWS
from .data_io import write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Restore the last published Teamplay datasets from the live GitHub Pages site."
    )
    parser.add_argument("--site-base-url", required=True)
    parser.add_argument("--output-root", default="apps/web/public/data")
    parser.add_argument("--regions", nargs="+", default=SUPPORTED_REGIONS, choices=SUPPORTED_REGIONS)
    parser.add_argument("--tiers", nargs="+", default=SUPPORTED_TIERS, choices=SUPPORTED_TIERS)
    parser.add_argument("--windows", nargs="+", default=SUPPORTED_WINDOWS, choices=SUPPORTED_WINDOWS)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--workers", type=int, default=8)
    return parser


def _request_json(url: str, timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "leagueStats-ci/1.0 (+https://github.com/diegoaranab/leagueStats)",
            "Accept": "application/json,text/plain,*/*",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        payload = response.read()
    parsed = json.loads(payload.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object from {url}")
    return parsed


def _entry_key(entry: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(entry.get("region", "")),
        str(entry.get("tier", "")),
        str(entry.get("window", "")),
    )


def _expected_keys(regions: Iterable[str], tiers: Iterable[str], windows: Iterable[str]) -> set[Tuple[str, str, str]]:
    return {(region, tier, window) for region in regions for tier in tiers for window in windows}


def _validate_teamplay_dataset(payload: Dict[str, Any], *, key: Tuple[str, str, str]) -> None:
    meta = payload.get("meta")
    data = payload.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        raise ValueError(f"Published Teamplay dataset {key} is missing meta/data objects")
    if meta.get("mode") != "teamplay":
        raise ValueError(f"Published Teamplay dataset {key} has unexpected mode={meta.get('mode')!r}")
    if (meta.get("region"), meta.get("tier"), meta.get("window")) != key:
        raise ValueError(f"Published Teamplay dataset {key} has mismatched metadata")


def restore_published_teamplay(
    *,
    site_base_url: str,
    output_root: Path,
    regions: list[str],
    tiers: list[str],
    windows: list[str],
    timeout: int,
    workers: int,
) -> int:
    base_url = site_base_url.rstrip("/")
    manifest_url = f"{base_url}/data/manifest.json"
    manifest = _request_json(manifest_url, timeout)

    expected = _expected_keys(regions, tiers, windows)
    entries: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for entry in manifest.get("datasets", []):
        if not isinstance(entry, dict) or entry.get("mode") != "teamplay":
            continue
        key = _entry_key(entry)
        if key in expected:
            entries[key] = entry

    missing_entries = sorted(expected - set(entries))
    if missing_entries:
        raise RuntimeError(
            f"Published manifest is missing {len(missing_entries)} expected Teamplay entries; "
            f"examples={missing_entries[:5]}"
        )

    temp_root = output_root / ".published_teamplay_restore"
    shutil.rmtree(temp_root, ignore_errors=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    def download_one(item: tuple[Tuple[str, str, str], Dict[str, Any]]) -> tuple[Tuple[str, str, str], Dict[str, Any]]:
        key, entry = item
        path = str(entry.get("path", ""))
        if not path.startswith("/data/teamplay/"):
            raise ValueError(f"Unexpected Teamplay manifest path for {key}: {path!r}")
        url = f"{base_url}/{path.lstrip('/')}"
        payload = _request_json(url, timeout)
        _validate_teamplay_dataset(payload, key=key)
        return key, payload

    downloaded: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    try:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            futures = [executor.submit(download_one, item) for item in entries.items()]
            for future in as_completed(futures):
                key, payload = future.result()
                downloaded[key] = payload

        if set(downloaded) != expected:
            missing = sorted(expected - set(downloaded))
            raise RuntimeError(f"Published Teamplay restore incomplete; missing={missing[:5]}")

        for (region, tier, window), payload in downloaded.items():
            write_json(temp_root / region / tier / f"{window}.json", payload)

        teamplay_root = output_root / "teamplay"
        shutil.rmtree(teamplay_root, ignore_errors=True)
        temp_root.replace(teamplay_root)
        write_json(output_root / "manifest.json", manifest)
    except Exception:
        shutil.rmtree(temp_root, ignore_errors=True)
        raise

    print(
        f"[DONE] Restored {len(downloaded)} published Teamplay datasets from {site_base_url} "
        "as a last-known-good fallback."
    )
    return len(downloaded)


def main() -> None:
    args = build_parser().parse_args()
    restore_published_teamplay(
        site_base_url=args.site_base_url,
        output_root=Path(args.output_root).resolve(),
        regions=list(args.regions),
        tiers=list(args.tiers),
        windows=list(args.windows),
        timeout=args.timeout,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()

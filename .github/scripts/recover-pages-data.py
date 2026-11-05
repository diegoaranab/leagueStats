#!/usr/bin/env python3
"""Recover the expected production matrix from the currently deployed Pages site."""

from __future__ import annotations

import argparse
import json
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


MODES = ("solo", "teamplay")
MAX_JSON_BYTES = 25 * 1024 * 1024


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow normal redirects without letting a response change origins."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        resolved_url = urllib.parse.urljoin(req.full_url, newurl)
        old = urllib.parse.urlsplit(req.full_url)
        new = urllib.parse.urlsplit(resolved_url)
        if (old.scheme, old.hostname, old.port) != (new.scheme, new.hostname, new.port):
            raise ValueError(f"refusing cross-origin redirect to {resolved_url!r}")
        return super().redirect_request(req, fp, code, msg, headers, resolved_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--tiers", nargs="+", required=True)
    parser.add_argument("--windows", nargs="+", required=True)
    parser.add_argument("--lanes", nargs="+", required=True)
    return parser.parse_args()


def normalize_base_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Pages base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Pages base URL must not contain credentials, a query, or a fragment")
    return value.rstrip("/") + "/"


def fetch_json(opener: urllib.request.OpenerDirector, url: str) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "LeagueStats-Pages-Recovery"},
    )
    try:
        with opener.open(request, timeout=30) as response:
            payload_bytes = response.read(MAX_JSON_BYTES + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise ValueError(f"could not download {url}: {exc}") from exc

    if len(payload_bytes) > MAX_JSON_BYTES:
        raise ValueError(f"download from {url} exceeds {MAX_JSON_BYTES} bytes")
    try:
        payload = json.loads(payload_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"download from {url} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"download from {url} is not a JSON object")
    return payload, payload_bytes


def expected_datasets(
    regions: list[str], tiers: list[str], windows: list[str]
) -> list[tuple[tuple[str, str, str, str], Path, str]]:
    expected = []
    for mode in MODES:
        prefix = Path("teamplay") if mode == "teamplay" else Path()
        for region in regions:
            for tier in tiers:
                for window in windows:
                    relative = prefix / region / tier / f"{window}.json"
                    key = (mode, region, tier, window)
                    expected.append((key, relative, f"/data/{relative.as_posix()}"))
    return expected


def validate_manifest_for_download(
    manifest: dict[str, Any],
    *,
    regions: list[str],
    tiers: list[str],
    windows: list[str],
    lanes: list[str],
) -> list[tuple[Path, str]]:
    supported = manifest.get("supported")
    entries = manifest.get("datasets")
    if not isinstance(supported, dict) or not isinstance(entries, list):
        raise ValueError("Pages manifest must contain supported metadata and a datasets array")

    expected_supported = {
        "regions": regions,
        "tiers": tiers,
        "windows": windows,
        "lanes": lanes,
        "modes": list(MODES),
    }
    for field, expected in expected_supported.items():
        actual = supported.get(field)
        if not isinstance(actual, list) or set(actual) != set(expected):
            raise ValueError(
                f"Pages manifest supported.{field} does not match production: "
                f"expected={expected}, actual={actual}"
            )

    indexed: dict[tuple[Any, Any, Any, Any], dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Pages manifest contains a non-object dataset entry")
        key = (entry.get("mode"), entry.get("region"), entry.get("tier"), entry.get("window"))
        if key in indexed:
            raise ValueError(f"Pages manifest contains duplicate dataset {key}")
        indexed[key] = entry

    expected = expected_datasets(regions, tiers, windows)
    if len(indexed) != len(expected):
        raise ValueError(
            f"Pages manifest must describe exactly {len(expected)} production datasets"
        )

    downloads = []
    for key, relative, public_path in expected:
        entry = indexed.get(key)
        if entry is None:
            raise ValueError(f"Pages manifest is missing dataset {key}")
        if entry.get("path") != public_path:
            raise ValueError(
                f"Pages manifest dataset {key} has unsafe path {entry.get('path')!r}; "
                f"expected {public_path!r}"
            )
        downloads.append((relative, public_path.removeprefix("/")))
    return downloads


def recover(args: argparse.Namespace) -> None:
    base_url = normalize_base_url(args.base_url)
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise ValueError(f"output root already exists: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)

    opener = urllib.request.build_opener(SameOriginRedirectHandler())
    manifest_url = urllib.parse.urljoin(base_url, "data/manifest.json")
    manifest, manifest_bytes = fetch_json(opener, manifest_url)
    downloads = validate_manifest_for_download(
        manifest,
        regions=args.regions,
        tiers=args.tiers,
        windows=args.windows,
        lanes=args.lanes,
    )

    with tempfile.TemporaryDirectory(prefix="pages-data-", dir=output_root.parent) as temp_dir:
        staging_root = Path(temp_dir)
        (staging_root / "manifest.json").write_bytes(manifest_bytes)
        for relative, public_path in downloads:
            destination = (staging_root / relative).resolve()
            if not destination.is_relative_to(staging_root.resolve()):
                raise ValueError(f"refusing destination outside recovery root: {relative}")
            _, payload_bytes = fetch_json(opener, urllib.parse.urljoin(base_url, public_path))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload_bytes)
        staging_root.rename(output_root)

    print(f"Recovered {len(downloads)} production datasets from {base_url}")


def main() -> None:
    try:
        recover(parse_args())
    except ValueError as exc:
        raise SystemExit(f"Pages recovery failed: {exc}") from exc


if __name__ == "__main__":
    main()

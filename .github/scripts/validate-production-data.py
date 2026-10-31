#!/usr/bin/env python3
"""Validate a complete LeagueStats production-data snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MODES = ("solo", "teamplay")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--tiers", nargs="+", required=True)
    parser.add_argument("--windows", nargs="+", required=True)
    parser.add_argument("--lanes", nargs="+", required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return payload


def validate_dataset(path: Path, lanes: list[str]) -> None:
    payload = load_json(path)
    meta = payload.get("meta")
    data = payload.get("data")
    if not isinstance(meta, dict) or not isinstance(data, dict):
        raise ValueError(f"{path} must contain object-valued meta and data fields")
    if meta.get("is_partial"):
        raise ValueError(f"{path} is marked partial")
    if meta.get("failed_lanes"):
        raise ValueError(f"{path} reports failed lanes: {meta['failed_lanes']}")

    missing_lanes = [lane for lane in lanes if not isinstance(data.get(lane), list)]
    if missing_lanes:
        raise ValueError(f"{path} is missing lane arrays: {missing_lanes}")
    if not any(data[lane] for lane in lanes):
        raise ValueError(f"{path} contains no champions")


def main() -> None:
    args = parse_args()
    manifest_path = args.root / "manifest.json"
    manifest = load_json(manifest_path)
    supported = manifest.get("supported")
    entries = manifest.get("datasets")
    if not isinstance(supported, dict) or not isinstance(entries, list):
        raise ValueError("manifest must contain supported metadata and a datasets array")

    expected_supported = {
        "regions": args.regions,
        "tiers": args.tiers,
        "windows": args.windows,
        "lanes": args.lanes,
        "modes": list(MODES),
    }
    for field, expected in expected_supported.items():
        actual = supported.get(field)
        if not isinstance(actual, list) or set(actual) != set(expected):
            raise ValueError(
                f"manifest supported.{field} does not match production: "
                f"expected={expected}, actual={actual}"
            )

    indexed_entries = {
        (entry.get("mode"), entry.get("region"), entry.get("tier"), entry.get("window")): entry
        for entry in entries
        if isinstance(entry, dict)
    }
    expected_count = len(MODES) * len(args.regions) * len(args.tiers) * len(args.windows)
    if len(indexed_entries) != expected_count:
        raise ValueError(
            f"manifest does not describe exactly {expected_count} production datasets; "
            f"found {len(indexed_entries)}"
        )

    for mode in MODES:
        for region in args.regions:
            for tier in args.tiers:
                for window in args.windows:
                    key = (mode, region, tier, window)
                    entry = indexed_entries.get(key)
                    if entry is None:
                        raise ValueError(f"manifest is missing dataset {key}")
                    if entry.get("status") != "ok" or entry.get("is_partial"):
                        raise ValueError(f"manifest dataset {key} is not complete: {entry}")
                    if entry.get("failed_lanes"):
                        raise ValueError(f"manifest dataset {key} reports failed lanes")
                    if not isinstance(entry.get("champion_count"), int) or entry["champion_count"] <= 0:
                        raise ValueError(f"manifest dataset {key} has no champions")

                    prefix = Path("teamplay") if mode == "teamplay" else Path()
                    dataset_path = args.root / prefix / region / tier / f"{window}.json"
                    expected_path = f"/data/{prefix.as_posix() + '/' if prefix.parts else ''}{region}/{tier}/{window}.json"
                    if entry.get("path") != expected_path:
                        raise ValueError(
                            f"manifest dataset {key} has unexpected path {entry.get('path')!r}"
                        )
                    validate_dataset(dataset_path, args.lanes)

    print(f"Validated {expected_count} complete production datasets under {args.root}.")


if __name__ == "__main__":
    main()

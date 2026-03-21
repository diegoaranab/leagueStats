from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

from .config import DEFAULT_LANES, SUPPORTED_REGIONS, SUPPORTED_TIERS, SUPPORTED_WINDOWS
from .data_io import load_existing_dataset, write_json

MANIFEST_SOURCE = "loltee_scraper"
SUPPORTED_MODES = ["solo", "teamplay"]


def infer_manifest_mode(entry: Dict[str, Any]) -> str:
    mode = entry.get("mode")
    if mode in SUPPORTED_MODES:
        return str(mode)

    path = str(entry.get("path", ""))
    if path.startswith("/data/teamplay/"):
        return "teamplay"

    return "solo"


def normalize_manifest_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {
        "mode": infer_manifest_mode(entry),
        "region": entry.get("region"),
        "tier": entry.get("tier"),
        "window": entry.get("window"),
        "path": entry.get("path"),
        "status": entry.get("status", "ok"),
        "generated_at_utc": entry.get("generated_at_utc"),
        "is_partial": bool(entry.get("is_partial")),
        "failed_lanes": list(entry.get("failed_lanes", [])),
        "warnings": list(entry.get("warnings", [])),
        "champion_count": int(entry.get("champion_count", 0) or 0),
    }

    if "error" in entry:
        normalized["error"] = entry.get("error")

    return normalized


def manifest_entry_key(entry: Dict[str, Any]) -> Tuple[str, Any, Any, Any]:
    return (
        infer_manifest_mode(entry),
        entry.get("region"),
        entry.get("tier"),
        entry.get("window"),
    )


def ordered_supported_values(values: Iterable[str], canonical_order: List[str]) -> List[str]:
    value_set = {value for value in values if value in canonical_order}
    return [value for value in canonical_order if value in value_set]


def sort_manifest_entries(entries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    region_order = {value: idx for idx, value in enumerate(SUPPORTED_REGIONS)}
    tier_order = {value: idx for idx, value in enumerate(SUPPORTED_TIERS)}
    window_order = {value: idx for idx, value in enumerate(SUPPORTED_WINDOWS)}
    mode_order = {value: idx for idx, value in enumerate(SUPPORTED_MODES)}

    return sorted(
        entries,
        key=lambda entry: (
            mode_order.get(infer_manifest_mode(entry), len(mode_order)),
            region_order.get(entry.get("region"), len(region_order)),
            tier_order.get(entry.get("tier"), len(tier_order)),
            window_order.get(entry.get("window"), len(window_order)),
        ),
    )


def merge_manifest(
    *,
    existing_manifest: Dict[str, Any] | None,
    new_entries: List[Dict[str, Any]],
    regions: List[str],
    tiers: List[str],
    windows: List[str],
    lanes: List[str],
    modes: List[str],
) -> Dict[str, Any]:
    merged_entries: Dict[Tuple[str, Any, Any, Any], Dict[str, Any]] = {}

    if isinstance(existing_manifest, dict):
        for entry in existing_manifest.get("datasets", []):
            if isinstance(entry, dict):
                normalized = normalize_manifest_entry(entry)
                merged_entries[manifest_entry_key(normalized)] = normalized

    for entry in new_entries:
        normalized = normalize_manifest_entry(entry)
        merged_entries[manifest_entry_key(normalized)] = normalized

    all_entries = sort_manifest_entries(merged_entries.values())

    existing_supported = existing_manifest.get("supported", {}) if isinstance(existing_manifest, dict) else {}
    existing_modes = existing_supported.get("modes", []) if isinstance(existing_supported, dict) else []

    supported_modes = ordered_supported_values(
        list(existing_modes)
        + list(modes)
        + [infer_manifest_mode(entry) for entry in all_entries],
        SUPPORTED_MODES,
    )

    return {
        "meta": {
            "source": MANIFEST_SOURCE,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "supported": {
            "regions": ordered_supported_values(
                list(existing_supported.get("regions", [])) + regions,
                SUPPORTED_REGIONS,
            ),
            "tiers": ordered_supported_values(
                list(existing_supported.get("tiers", [])) + tiers,
                SUPPORTED_TIERS,
            ),
            "windows": ordered_supported_values(
                list(existing_supported.get("windows", [])) + windows,
                SUPPORTED_WINDOWS,
            ),
            "lanes": ordered_supported_values(
                list(existing_supported.get("lanes", [])) + lanes,
                DEFAULT_LANES,
            ),
            "modes": supported_modes,
        },
        "datasets": all_entries,
    }


def load_manifest(path) -> Dict[str, Any] | None:
    payload = load_existing_dataset(path)
    return payload if isinstance(payload, dict) else None


def write_manifest(path, manifest: Dict[str, Any]) -> None:
    write_json(path, manifest)

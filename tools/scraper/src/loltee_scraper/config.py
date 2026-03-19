from __future__ import annotations

from typing import Iterable, List

DEFAULT_LANES = ["top", "jungle", "middle", "bottom", "support"]
SUPPORTED_REGIONS = ["na", "lan", "las"]
SUPPORTED_TIERS = [
    "bronze",
    "silver",
    "gold_plus",
    "platinum_plus",
    "emerald_plus",
    "diamond_plus",
    "d2_plus",
    "master_plus",
]
SUPPORTED_WINDOWS = ["current", "7d", "14d"]

# `current` uses the default tierlist page with no explicit patch query param.
WINDOW_PATCH_QUERY_VALUES = {
    "current": None,
    "7d": "7",
    "14d": "14",
}


def normalize_lanes(lanes: Iterable[str]) -> List[str]:
    seen = set()
    normalized: List[str] = []

    for lane in lanes:
        if lane not in DEFAULT_LANES:
            raise ValueError(f"Unsupported lane: {lane}")
        if lane not in seen:
            normalized.append(lane)
            seen.add(lane)

    if not normalized:
        raise ValueError("At least one lane is required")

    return normalized

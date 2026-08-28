from __future__ import annotations

import unittest

from loltee_scraper.config import DEFAULT_LANES, SUPPORTED_TIERS
from loltee_scraper.manifest import merge_manifest
from loltee_scraper.scraper import build_tierlist_url, validate_window_url_builder


EXPECTED_TIERS = [
    "iron",
    "bronze",
    "silver",
    "gold",
    "platinum",
    "emerald",
    "diamond",
    "master",
]


class ExactRankSemanticsTests(unittest.TestCase):
    def test_supported_tiers_are_exact_rank_brackets(self) -> None:
        self.assertEqual(SUPPORTED_TIERS, EXPECTED_TIERS)

    def test_tierlist_urls_use_exact_rank_values(self) -> None:
        self.assertEqual(
            build_tierlist_url(lane="middle", tier="gold", region="lan", window="7d"),
            "https://lolalytics.com/lol/tierlist/?lane=middle&tier=gold&region=lan&patch=7",
        )
        validate_window_url_builder()

    def test_manifest_prunes_legacy_tiers_and_exposes_canonical_set(self) -> None:
        existing_manifest = {
            "supported": {
                "regions": ["na"],
                "tiers": ["gold_plus", "d2_plus"],
                "windows": ["7d"],
                "lanes": DEFAULT_LANES,
                "modes": ["solo"],
            },
            "datasets": [
                {
                    "region": "na",
                    "tier": "gold_plus",
                    "window": "7d",
                    "path": "/data/na/gold_plus/7d.json",
                },
                {
                    "region": "na",
                    "tier": "diamond",
                    "window": "7d",
                    "path": "/data/na/diamond/7d.json",
                },
            ],
        }

        manifest = merge_manifest(
            existing_manifest=existing_manifest,
            new_entries=[],
            regions=["na"],
            tiers=["diamond"],
            windows=["7d"],
            lanes=DEFAULT_LANES,
            modes=["solo"],
        )

        self.assertEqual(manifest["supported"]["tiers"], EXPECTED_TIERS)
        self.assertEqual(
            [entry["tier"] for entry in manifest["datasets"]],
            ["diamond"],
        )


if __name__ == "__main__":
    unittest.main()

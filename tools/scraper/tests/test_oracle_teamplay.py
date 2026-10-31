from __future__ import annotations

import unittest
from pathlib import Path

from loltee_scraper.oracle_teamplay import (
    TEAMPLAY_LEAGUES,
    load_oracle_teamplay_snapshot,
    select_latest_patches,
)


FIXTURES = Path(__file__).parent / "fixtures"


class OracleTeamplayCoverageTests(unittest.TestCase):
    def test_teamplay_competitions_include_verified_international_events(self) -> None:
        self.assertEqual(
            TEAMPLAY_LEAGUES,
            ["LCK", "LPL", "LEC", "LCS", "WLDs", "MSI", "FST"],
        )
        self.assertNotIn("EM", TEAMPLAY_LEAGUES)

    def test_worlds_participates_in_dynamic_latest_patch_selection(self) -> None:
        snapshot = load_oracle_teamplay_snapshot(
            FIXTURES / "oracle_teamplay_international.csv"
        )

        self.assertEqual(snapshot.leagues_used, TEAMPLAY_LEAGUES)
        self.assertEqual(snapshot.patches_used, ["16.18", "16.19", "16.20"])
        self.assertNotIn("16.16", snapshot.patches_used)
        self.assertNotIn("16.17", snapshot.patches_used)
        self.assertNotIn("99.99", snapshot.patches_used)
        self.assertEqual(snapshot.total_games_filtered, 3)
        self.assertEqual(snapshot.role_stats[("aurora", "top")].pro_pick_count, 1)
        self.assertNotIn(("excludedchampion", "top"), snapshot.role_stats)

    def test_latest_three_patches_remain_numeric_and_dynamic(self) -> None:
        patches = select_latest_patches(
            FIXTURES / "oracle_patch_selection.csv",
            leagues=TEAMPLAY_LEAGUES,
        )

        self.assertEqual(patches, ["27.2", "27.3", "27.10"])
        self.assertNotIn("27.1", patches)
        self.assertNotIn("100.1", patches)

    def test_existing_pick_and_ban_deduplication_is_unchanged(self) -> None:
        snapshot = load_oracle_teamplay_snapshot(
            FIXTURES / "oracle_teamplay_international.csv"
        )

        self.assertEqual(snapshot.duplicate_pick_rows_skipped, 1)
        self.assertEqual(snapshot.duplicate_bans_skipped, 1)
        self.assertEqual(snapshot.role_stats[("aurora", "top")].pro_pick_count, 1)
        self.assertEqual(snapshot.champion_stats["yone"].pro_ban_count, 1)


if __name__ == "__main__":
    unittest.main()

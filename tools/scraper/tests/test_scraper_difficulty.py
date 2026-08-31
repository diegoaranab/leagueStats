from __future__ import annotations

import unittest
from datetime import date, timedelta

from loltee_scraper.build_teamplay import build_teamplay_dataset
from loltee_scraper.difficulty_scoring import build_series_key
from loltee_scraper.oracle_teamplay import (
    OracleChampionStats,
    OracleRoleStats,
    OracleTeamplaySnapshot,
)
from loltee_scraper.scraper import compute_mastery_fields, post_process_data


TODAY = date(2026, 8, 30)


def champion(name: str, rank: int, mastery_gap_pct: float) -> dict[str, object]:
    return {
        "lane": "middle",
        "rank": rank,
        "name": name,
        "win_rate": 100.0 - mastery_gap_pct,
        "delta": mastery_gap_pct,
    }


def observation(age_days: int, value: float) -> dict[str, object]:
    return {
        "date": (TODAY - timedelta(days=age_days)).isoformat(),
        "delta": value,
        "win_rate": 50.0,
        "mastery_gap_pct": value,
    }


def dataset(champions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "meta": {
            "region": "lan",
            "tier": "gold",
            "window": "7d",
            "generated_at_utc": "2026-08-30T12:23:00+00:00",
            "is_partial": False,
            "failed_lanes": [],
            "warnings": [],
        },
        "data": {"middle": champions},
    }


class ScraperDifficultyIntegrationTests(unittest.TestCase):
    def test_bootstrap_labels_follow_current_mastery_signal(self) -> None:
        result = post_process_data(
            dataset(
                [
                    champion("Low", 1, 1.0),
                    champion("Middle", 2, 10.0),
                    champion("High", 3, 20.0),
                ]
            ),
            observation_date=TODAY,
        )
        lane = result["data"]["middle"]

        self.assertEqual([item["difficulty_score"] for item in lane], [1.0, 10.0, 20.0])
        self.assertEqual([item["difficulty"] for item in lane], ["easy", "medium", "hard"])
        self.assertTrue(all(item["difficulty_history_samples"] == 1 for item in lane))
        self.assertTrue(all(not item["difficulty_history_applied"] for item in lane))

    def test_tertiles_use_smoothed_score_instead_of_current_snapshot(self) -> None:
        champions = [
            champion("HistoricallyHigh", 1, 1.0),
            champion("Stable", 2, 10.0),
            champion("HistoricallyLow", 3, 20.0),
        ]
        historical_values = {
            "HistoricallyHigh": 30.0,
            "Stable": 10.0,
            "HistoricallyLow": 0.0,
        }
        history = {
            "series": {
                build_series_key(
                    region="lan",
                    tier="gold",
                    window="7d",
                    lane="middle",
                    champion=name,
                ): [observation(age_days, value) for age_days in range(1, 7)]
                for name, value in historical_values.items()
            }
        }

        result = post_process_data(
            dataset(champions),
            difficulty_history=history,
            observation_date=TODAY,
        )
        by_name = {item["name"]: item for item in result["data"]["middle"]}

        self.assertEqual(by_name["HistoricallyHigh"]["mastery_gap_pct"], 1.0)
        self.assertEqual(by_name["HistoricallyLow"]["mastery_gap_pct"], 20.0)
        self.assertGreater(
            by_name["HistoricallyHigh"]["difficulty_score"],
            by_name["HistoricallyLow"]["difficulty_score"],
        )
        self.assertEqual(by_name["HistoricallyHigh"]["difficulty"], "hard")
        self.assertEqual(by_name["HistoricallyLow"]["difficulty"], "easy")
        self.assertTrue(all(item["difficulty_history_applied"] for item in by_name.values()))
        self.assertEqual(result["meta"]["difficulty_history_smoothed_count"], 3)
        self.assertEqual(result["meta"]["difficulty_history_fallback_count"], 0)
        self.assertEqual(
            result["meta"]["difficulty_method"],
            "lane_relative_robust_recency_mastery_gap_pct_tertiles_v2",
        )

    def test_current_mastery_formula_is_unchanged(self) -> None:
        item = {"win_rate": 50.0, "delta": 5.0}

        compute_mastery_fields(item)

        self.assertEqual(item["best_win_est"], 55.0)
        self.assertEqual(item["mastery_gap_raw"], 5.0)
        self.assertEqual(item["mastery_gap_pct"], 9.09)


class TeamplayDifficultyRegressionTests(unittest.TestCase):
    def test_teamplay_copies_difficulty_but_keeps_pro_driven_ranking(self) -> None:
        solo = dataset(
            [
                {
                    **champion("Alpha", 1, 10.0),
                    "filtered_rank": 1,
                    "difficulty": "hard",
                    "difficulty_score": 30.0,
                    "difficulty_history_samples": 7,
                    "difficulty_history_applied": True,
                },
                {
                    **champion("Beta", 2, 10.0),
                    "filtered_rank": 2,
                    "difficulty": "easy",
                    "difficulty_score": 1.0,
                    "difficulty_history_samples": 7,
                    "difficulty_history_applied": True,
                },
            ]
        )
        role_stats = {
            ("alpha", "middle"): OracleRoleStats(5, 0.2, 3, 0.6, 10, 1.0, 0.0),
            ("beta", "middle"): OracleRoleStats(5, 0.8, 3, 0.6, 10, 1.0, 0.0),
        }
        champion_stats = {
            name: OracleChampionStats(0, 0.0, 1, 5) for name in ("alpha", "beta")
        }
        snapshot = OracleTeamplaySnapshot(
            leagues_used=["LCK"],
            patches_used=["26.16"],
            total_games_filtered=10,
            role_stats=role_stats,
            champion_stats=champion_stats,
            lane_max_role_pick_rate={"middle": 0.8},
            lane_max_role_adjusted_ban_rate={"middle": 0.0},
            global_max_ban_rate=0.0,
            is_partial=False,
            warnings=[],
            duplicate_pick_rows_skipped=0,
            duplicate_bans_skipped=0,
        )

        result = build_teamplay_dataset(
            solo_dataset=solo,
            pro_snapshot=snapshot,
            region="lan",
            tier="gold",
            window="7d",
        )
        lane = result["data"]["middle"]

        self.assertEqual([item["name"] for item in lane], ["Beta", "Alpha"])
        self.assertEqual([item["teamplay_rank"] for item in lane], [1, 2])
        self.assertEqual(lane[0]["difficulty"], "easy")
        self.assertTrue(lane[0]["difficulty_history_applied"])


if __name__ == "__main__":
    unittest.main()

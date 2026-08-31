from __future__ import annotations

import unittest
from datetime import date, timedelta

from loltee_scraper.difficulty_scoring import (
    MAD_SCALE_FACTOR,
    build_series_key,
    compute_difficulty_score,
    effective_observation_series,
    recency_weighted_mean,
    select_history_series,
    winsorize_median_mad,
)


TODAY = date(2026, 8, 30)
CONTEXT = {
    "region": "lan",
    "tier": "gold",
    "window": "7d",
    "lane": "middle",
    "champion": "Ahri",
}


def observation(age_days: int, value: float) -> dict[str, object]:
    return {
        "date": (TODAY - timedelta(days=age_days)).isoformat(),
        "delta": value,
        "win_rate": 50.0,
        "mastery_gap_pct": value,
    }


def history_for(items: list[dict[str, object]], **overrides: str) -> dict[str, object]:
    context = CONTEXT | overrides
    key = build_series_key(**context)
    return {"series": {key: items}}


class EffectiveSeriesTests(unittest.TestCase):
    def test_no_history_uses_current_value(self) -> None:
        result = compute_difficulty_score(
            None,
            **CONTEXT,
            current_observation_date=TODAY,
            current_value=12.34,
        )

        self.assertEqual(result.value, 12.34)
        self.assertEqual(result.sample_count, 1)
        self.assertFalse(result.history_applied)

    def test_one_through_six_effective_observations_use_fallback(self) -> None:
        for effective_count in range(1, 7):
            with self.subTest(effective_count=effective_count):
                persisted = [
                    observation(age_days, float(age_days))
                    for age_days in range(1, effective_count)
                ]
                result = compute_difficulty_score(
                    history_for(persisted),
                    **CONTEXT,
                    current_observation_date=TODAY,
                    current_value=25.0,
                )
                self.assertEqual(result.value, 25.0)
                self.assertEqual(result.sample_count, effective_count)
                self.assertFalse(result.history_applied)

    def test_exactly_seven_observations_activate_smoothing(self) -> None:
        persisted = [observation(age_days, 10.0) for age_days in range(1, 7)]

        result = compute_difficulty_score(
            history_for(persisted),
            **CONTEXT,
            current_observation_date=TODAY,
            current_value=20.0,
        )

        self.assertEqual(result.sample_count, 7)
        self.assertTrue(result.history_applied)
        self.assertNotEqual(result.value, 20.0)

    def test_current_value_replaces_same_day_persisted_value(self) -> None:
        persisted = [observation(1, 5.0), observation(0, 999.0)]
        effective = effective_observation_series(
            persisted,
            current_observation_date=TODAY,
            current_value=12.0,
        )

        self.assertEqual(len(effective), 2)
        self.assertEqual(effective[-1], (TODAY, 12.0))
        self.assertEqual(persisted[-1]["mastery_gap_pct"], 999.0)

    def test_old_and_future_observations_are_excluded(self) -> None:
        effective = effective_observation_series(
            [
                observation(29, 1.0),
                observation(30, 2.0),
                observation(-1, 3.0),
            ],
            current_observation_date=TODAY,
            current_value=4.0,
        )

        self.assertEqual(effective, [(TODAY - timedelta(days=29), 1.0), (TODAY, 4.0)])

    def test_context_selection_is_fully_isolated(self) -> None:
        exact = [observation(age_days, 10.0) for age_days in range(1, 7)]
        series = {
            build_series_key(**CONTEXT): exact,
            build_series_key(**(CONTEXT | {"tier": "silver"})): [observation(1, 100.0)],
            build_series_key(**(CONTEXT | {"region": "na"})): [observation(1, 200.0)],
            build_series_key(**(CONTEXT | {"lane": "top"})): [observation(1, 300.0)],
            build_series_key(**(CONTEXT | {"window": "14d"})): [observation(1, 400.0)],
            build_series_key(**(CONTEXT | {"champion": "Lux"})): [observation(1, 500.0)],
        }
        history = {"series": series}

        selected = select_history_series(history, **CONTEXT)
        result = compute_difficulty_score(
            history,
            **CONTEXT,
            current_observation_date=TODAY,
            current_value=20.0,
        )

        self.assertIs(selected, exact)
        self.assertEqual(result.sample_count, 7)
        self.assertLess(result.value, 20.0)


class RobustWeightingTests(unittest.TestCase):
    def test_hand_verifiable_half_life_fixture(self) -> None:
        score = recency_weighted_mean(
            [(TODAY, 10.0), (TODAY - timedelta(days=7), 20.0)],
            current_observation_date=TODAY,
        )

        self.assertAlmostEqual(score, 13.333333333333334)

    def test_missing_calendar_days_use_actual_date_age(self) -> None:
        one_day_old = recency_weighted_mean(
            [(TODAY, 10.0), (TODAY - timedelta(days=1), 20.0)],
            current_observation_date=TODAY,
        )
        seven_days_old = recency_weighted_mean(
            [(TODAY, 10.0), (TODAY - timedelta(days=7), 20.0)],
            current_observation_date=TODAY,
        )

        self.assertGreater(one_day_old, seven_days_old)

    def test_recent_value_has_more_influence_than_old_value(self) -> None:
        recent_high = recency_weighted_mean(
            [(TODAY, 20.0), (TODAY - timedelta(days=14), 10.0)],
            current_observation_date=TODAY,
        )
        recent_low = recency_weighted_mean(
            [(TODAY, 10.0), (TODAY - timedelta(days=14), 20.0)],
            current_observation_date=TODAY,
        )

        self.assertGreater(recent_high, recent_low)

    def test_seven_day_observation_has_half_weight(self) -> None:
        score = recency_weighted_mean(
            [(TODAY, 0.0), (TODAY - timedelta(days=7), 1.0)],
            current_observation_date=TODAY,
        )

        self.assertAlmostEqual(score, 0.5 / 1.5)

    def test_severe_outlier_is_mad_winsorized(self) -> None:
        values = [8.0, 9.0, 10.0, 10.0, 11.0, 12.0, 1000.0]

        clamped = winsorize_median_mad(values)

        self.assertEqual(clamped[:-1], values[:-1])
        self.assertAlmostEqual(clamped[-1], 10.0 + (3 * MAD_SCALE_FACTOR))

    def test_zero_mad_explicitly_leaves_values_unchanged(self) -> None:
        values = [10.0, 10.0, 10.0, 10.0, 1000.0]

        self.assertEqual(winsorize_median_mad(values), values)

    def test_same_input_is_exactly_deterministic(self) -> None:
        persisted = [observation(age_days, 8.0 + age_days) for age_days in range(1, 7)]
        arguments = {
            **CONTEXT,
            "current_observation_date": TODAY,
            "current_value": 14.0,
        }

        first = compute_difficulty_score(history_for(persisted), **arguments)
        second = compute_difficulty_score(history_for(persisted), **arguments)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

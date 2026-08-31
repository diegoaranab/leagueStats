from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any, Mapping, Sequence


RETENTION_DAYS = 30
MIN_HISTORY_SAMPLES = 7
HALF_LIFE_DAYS = 7
MAD_SCALE_FACTOR = 1.4826
MAD_SIGMA_LIMIT = 3

DifficultyObservation = tuple[date, float]


@dataclass(frozen=True, slots=True)
class DifficultyScore:
    value: float
    sample_count: int
    history_applied: bool


def build_series_key(
    *,
    region: str,
    tier: str,
    window: str,
    lane: str,
    champion: str,
) -> str:
    return "|".join((region, tier, window, lane, champion))


def select_history_series(
    history: Mapping[str, Any] | None,
    *,
    region: str,
    tier: str,
    window: str,
    lane: str,
    champion: str,
) -> Sequence[Mapping[str, Any]]:
    if history is None:
        return ()
    series = history.get("series")
    if not isinstance(series, Mapping):
        return ()
    selected = series.get(
        build_series_key(
            region=region,
            tier=tier,
            window=window,
            lane=lane,
            champion=champion,
        )
    )
    if not isinstance(selected, list):
        return ()
    return selected


def effective_observation_series(
    persisted: Sequence[Mapping[str, Any]],
    *,
    current_observation_date: date,
    current_value: float,
    retention_days: int = RETENTION_DAYS,
) -> list[DifficultyObservation]:
    """Return distinct valid UTC dates, with the current scrape winning today."""

    by_date: dict[date, float] = {}
    for observation in persisted:
        try:
            observation_date = date.fromisoformat(str(observation["date"]))
            value = float(observation["mastery_gap_pct"])
        except (KeyError, TypeError, ValueError):
            continue
        age_days = (current_observation_date - observation_date).days
        if 0 <= age_days < retention_days and math.isfinite(value):
            by_date[observation_date] = value

    by_date[current_observation_date] = float(current_value)
    return sorted(by_date.items())


def winsorize_median_mad(values: Sequence[float]) -> list[float]:
    if not values:
        return []

    center = float(median(values))
    mad = float(median(abs(value - center) for value in values))
    if mad == 0:
        return [float(value) for value in values]

    robust_sigma = MAD_SCALE_FACTOR * mad
    lower = max(0.0, center - (MAD_SIGMA_LIMIT * robust_sigma))
    upper = center + (MAD_SIGMA_LIMIT * robust_sigma)
    return [min(max(float(value), lower), upper) for value in values]


def recency_weighted_mean(
    observations: Sequence[DifficultyObservation],
    *,
    current_observation_date: date,
    half_life_days: int = HALF_LIFE_DAYS,
) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for observation_date, value in observations:
        age_days = (current_observation_date - observation_date).days
        weight = 2 ** (-age_days / half_life_days)
        weighted_sum += value * weight
        total_weight += weight
    if total_weight == 0:
        raise ValueError("at least one observation is required")
    return weighted_sum / total_weight


def compute_difficulty_score(
    history: Mapping[str, Any] | None,
    *,
    region: str,
    tier: str,
    window: str,
    lane: str,
    champion: str,
    current_observation_date: date,
    current_value: float,
) -> DifficultyScore:
    persisted = select_history_series(
        history,
        region=region,
        tier=tier,
        window=window,
        lane=lane,
        champion=champion,
    )
    effective = effective_observation_series(
        persisted,
        current_observation_date=current_observation_date,
        current_value=current_value,
    )
    sample_count = len(effective)
    if sample_count < MIN_HISTORY_SAMPLES:
        return DifficultyScore(
            value=round(float(current_value), 2),
            sample_count=sample_count,
            history_applied=False,
        )

    clamped_values = winsorize_median_mad([value for _, value in effective])
    clamped_observations = [
        (observation_date, value)
        for (observation_date, _), value in zip(effective, clamped_values)
    ]
    score = recency_weighted_mean(
        clamped_observations,
        current_observation_date=current_observation_date,
    )
    return DifficultyScore(
        value=round(score, 2),
        sample_count=sample_count,
        history_applied=True,
    )

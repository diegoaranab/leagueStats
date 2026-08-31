from __future__ import annotations

import argparse
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
DEFAULT_RETENTION_DAYS = 30


class HistoryValidationError(ValueError):
    """Raised when persisted history or Solo input has an unsafe shape."""


def _is_number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _parse_date(value: object, *, field: str) -> date:
    if not isinstance(value, str):
        raise HistoryValidationError(f"{field} must be a YYYY-MM-DD string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HistoryValidationError(f"{field} must be a valid YYYY-MM-DD date") from exc
    if parsed.isoformat() != value:
        raise HistoryValidationError(f"{field} must use canonical YYYY-MM-DD format")
    return parsed


def _validate_optional_number(value: object, *, field: str) -> None:
    if value is not None and not _is_number(value):
        raise HistoryValidationError(f"{field} must be a finite number or null")


def new_history(retention_days: int = DEFAULT_RETENTION_DAYS) -> dict[str, Any]:
    if (
        isinstance(retention_days, bool)
        or not isinstance(retention_days, int)
        or retention_days < 1
    ):
        raise HistoryValidationError("retention_days must be a positive integer")
    return {
        "schema_version": SCHEMA_VERSION,
        "retention_days": retention_days,
        "updated_at_utc": None,
        "series": {},
    }


def validate_history(history: object) -> dict[str, Any]:
    if not isinstance(history, dict):
        raise HistoryValidationError("history must be a JSON object")
    required_top_level = {"schema_version", "retention_days", "updated_at_utc", "series"}
    if set(history) != required_top_level:
        raise HistoryValidationError(
            f"history must contain exactly {sorted(required_top_level)}"
        )
    if history.get("schema_version") != SCHEMA_VERSION:
        raise HistoryValidationError(
            f"unsupported history schema_version: {history.get('schema_version')!r}"
        )

    retention_days = history.get("retention_days")
    if (
        isinstance(retention_days, bool)
        or not isinstance(retention_days, int)
        or retention_days < 1
    ):
        raise HistoryValidationError("retention_days must be a positive integer")

    updated_at = history.get("updated_at_utc")
    if updated_at is not None:
        if not isinstance(updated_at, str):
            raise HistoryValidationError("updated_at_utc must be an ISO timestamp or null")
        try:
            parsed_updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HistoryValidationError("updated_at_utc must be an ISO timestamp or null") from exc
        if parsed_updated_at.tzinfo is None or parsed_updated_at.utcoffset() != timedelta(0):
            raise HistoryValidationError("updated_at_utc must include a UTC offset")

    series = history.get("series")
    if not isinstance(series, dict):
        raise HistoryValidationError("series must be a JSON object")

    for key, observations in series.items():
        key_parts = key.split("|") if isinstance(key, str) else []
        if len(key_parts) != 5 or not all(key_parts):
            raise HistoryValidationError(f"invalid series key: {key!r}")
        if not isinstance(observations, list):
            raise HistoryValidationError(f"series {key!r} must contain a list")
        for index, observation in enumerate(observations):
            prefix = f"series {key!r} observation {index}"
            if not isinstance(observation, dict):
                raise HistoryValidationError(f"{prefix} must be an object")
            required = {"date", "delta", "win_rate", "mastery_gap_pct"}
            if set(observation) != required:
                raise HistoryValidationError(f"{prefix} must contain exactly {sorted(required)}")
            _parse_date(observation["date"], field=f"{prefix}.date")
            _validate_optional_number(observation["delta"], field=f"{prefix}.delta")
            _validate_optional_number(observation["win_rate"], field=f"{prefix}.win_rate")
            if not _is_number(observation["mastery_gap_pct"]):
                raise HistoryValidationError(f"{prefix}.mastery_gap_pct must be a finite number")

    return history


def load_history(path: Path, retention_days: int = DEFAULT_RETENTION_DAYS) -> dict[str, Any]:
    if not path.exists():
        return new_history(retention_days)
    try:
        history = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoryValidationError(f"could not load history from {path}: {exc}") from exc
    return validate_history(history)


def _observation(
    observation_date: date,
    champion: Mapping[str, Any],
) -> dict[str, Any] | None:
    mastery_gap_pct = champion.get("mastery_gap_pct")
    if not _is_number(mastery_gap_pct):
        return None

    delta = champion.get("delta")
    win_rate = champion.get("win_rate")
    _validate_optional_number(delta, field="champion.delta")
    _validate_optional_number(win_rate, field="champion.win_rate")
    return {
        "date": observation_date.isoformat(),
        "delta": delta,
        "win_rate": win_rate,
        "mastery_gap_pct": mastery_gap_pct,
    }


def collect_solo_observations(
    data_root: Path,
    *,
    regions: Sequence[str],
    tiers: Sequence[str],
    windows: Sequence[str],
    lanes: Sequence[str],
    observation_date: date,
) -> list[tuple[str, dict[str, Any]]]:
    """Validate a complete Solo matrix, then return eligible observations."""

    datasets: list[tuple[str, str, str, Mapping[str, Any]]] = []
    for region in regions:
        for tier in tiers:
            for window in windows:
                dataset_path = data_root / region / tier / f"{window}.json"
                try:
                    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise HistoryValidationError(
                        f"could not load Solo dataset {dataset_path}: {exc}"
                    ) from exc
                if not isinstance(dataset, dict):
                    raise HistoryValidationError(f"Solo dataset {dataset_path} must be an object")

                meta = dataset.get("meta")
                data = dataset.get("data")
                if not isinstance(meta, dict) or not isinstance(data, dict):
                    raise HistoryValidationError(
                        f"Solo dataset {dataset_path} is missing meta/data objects"
                    )
                expected_context = {"region": region, "tier": tier, "window": window}
                for field, expected in expected_context.items():
                    if meta.get(field) != expected:
                        raise HistoryValidationError(
                            f"Solo dataset {dataset_path} has {field}={meta.get(field)!r}; "
                            f"expected {expected!r}"
                        )
                if meta.get("is_partial") is not False or meta.get("failed_lanes") != []:
                    raise HistoryValidationError(f"Solo dataset {dataset_path} is partial")
                for lane in lanes:
                    if not isinstance(data.get(lane), list):
                        raise HistoryValidationError(
                            f"Solo dataset {dataset_path} is missing complete lane {lane!r}"
                        )
                datasets.append((region, tier, window, data))

    observations: list[tuple[str, dict[str, Any]]] = []
    for region, tier, window, data in datasets:
        for lane in lanes:
            for champion in data[lane]:
                if not isinstance(champion, dict):
                    raise HistoryValidationError(
                        f"Solo context {region}/{tier}/{window}/{lane} contains a "
                        "non-object champion"
                    )
                champion_name = champion.get("name")
                if not isinstance(champion_name, str) or not champion_name.strip():
                    raise HistoryValidationError(
                        f"Solo context {region}/{tier}/{window}/{lane} contains a champion "
                        "without a name"
                    )
                observation = _observation(observation_date, champion)
                if observation is None:
                    continue
                key = "|".join((region, tier, window, lane, champion_name))
                observations.append((key, observation))
    return observations


def merge_observations(
    history: Mapping[str, Any],
    observations: Iterable[tuple[str, Mapping[str, Any]]],
    *,
    observation_date: date,
    updated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    validate_history(history)
    retention_days = history["retention_days"]
    cutoff = observation_date - timedelta(days=retention_days - 1)

    merged_by_key: dict[str, dict[str, dict[str, Any]]] = {}
    for key, existing_observations in history["series"].items():
        by_date: dict[str, dict[str, Any]] = {}
        for existing in existing_observations:
            existing_date = _parse_date(existing["date"], field=f"series {key!r}.date")
            if cutoff <= existing_date <= observation_date:
                by_date[existing["date"]] = dict(existing)
        if by_date:
            merged_by_key[key] = by_date

    for key, observation in observations:
        validate_history(
            {
                "schema_version": SCHEMA_VERSION,
                "retention_days": retention_days,
                "updated_at_utc": None,
                "series": {key: [dict(observation)]},
            }
        )
        if observation["date"] != observation_date.isoformat():
            raise HistoryValidationError(
                f"new observation date {observation['date']!r} does not match "
                f"merge date {observation_date.isoformat()!r}"
            )
        merged_by_key.setdefault(key, {})[observation["date"]] = dict(observation)

    normalized_series = {
        key: [by_date[item_date] for item_date in sorted(by_date)]
        for key, by_date in sorted(merged_by_key.items())
        if by_date
    }
    changed = normalized_series != history["series"]
    timestamp = history.get("updated_at_utc")
    if changed:
        timestamp_value = updated_at_utc or datetime.now(timezone.utc)
        if timestamp_value.tzinfo is None:
            raise HistoryValidationError("updated_at_utc must be timezone-aware")
        timestamp = timestamp_value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    result = {
        "schema_version": SCHEMA_VERSION,
        "retention_days": retention_days,
        "updated_at_utc": timestamp,
        "series": normalized_series,
    }
    return validate_history(result)


def merge_solo_matrix(
    history: Mapping[str, Any],
    data_root: Path,
    *,
    regions: Sequence[str],
    tiers: Sequence[str],
    windows: Sequence[str],
    lanes: Sequence[str],
    observation_date: date,
    updated_at_utc: datetime | None = None,
) -> dict[str, Any]:
    observations = collect_solo_observations(
        data_root,
        regions=regions,
        tiers=tiers,
        windows=windows,
        lanes=lanes,
        observation_date=observation_date,
    )
    return merge_observations(
        history,
        observations,
        observation_date=observation_date,
        updated_at_utc=updated_at_utc,
    )


def serialize_history(history: Mapping[str, Any]) -> str:
    validate_history(history)
    return json.dumps(history, ensure_ascii=False, indent=2) + "\n"


def write_history(path: Path, history: Mapping[str, Any]) -> None:
    payload = serialize_history(history)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _utc_date(value: str) -> date:
    return _parse_date(value, field="--date")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge a complete Solo matrix into difficulty history."
    )
    parser.add_argument("--history-file", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--regions", nargs="+", required=True)
    parser.add_argument("--tiers", nargs="+", required=True)
    parser.add_argument("--windows", nargs="+", required=True)
    parser.add_argument("--lanes", nargs="+", required=True)
    parser.add_argument("--date", type=_utc_date, default=datetime.now(timezone.utc).date())
    args = parser.parse_args()

    history = load_history(args.history_file)
    merged = merge_solo_matrix(
        history,
        args.data_root,
        regions=args.regions,
        tiers=args.tiers,
        windows=args.windows,
        lanes=args.lanes,
        observation_date=args.date,
    )
    write_history(args.history_file, merged)
    observation_count = sum(len(items) for items in merged["series"].values())
    print(
        f"Wrote {len(merged['series'])} difficulty series / {observation_count} observations "
        f"to {args.history_file}"
    )


if __name__ == "__main__":
    main()

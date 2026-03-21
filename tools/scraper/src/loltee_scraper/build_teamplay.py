from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .config import DEFAULT_LANES, SUPPORTED_REGIONS, SUPPORTED_TIERS, SUPPORTED_WINDOWS
from .data_io import (
    count_champions,
    is_partial_dataset,
    load_existing_dataset,
    update_last_success_backup,
    write_json,
)
from .manifest import load_manifest, merge_manifest, write_manifest
from .oracle_teamplay import (
    TEAMPLAY_LEAGUES,
    OracleChampionStats,
    OracleRoleStats,
    OracleTeamplaySnapshot,
    load_oracle_teamplay_snapshot,
)
from .oracle_teamplay import normalize_champion_key

BADGE_HIGH_PRO_PRESENCE = "High Pro Presence"
BADGE_DRAFT_PRIORITY = "Draft Priority"
BADGE_FLEX_PICK = "Flex Pick"
BADGE_STRONG_IN_SOLO = "Strong in Solo"
STRICT_PRO_EVIDENCE_MODE = "strict_pro_evidence_v2"
TEAMPLAY_RANK_MODE = "teamplay_blend_v3"
TEAMPLAY_SCORE_FORMULA = "0.90*pro_score_v3 + 0.10*solo_strength_score"
TEAMPLAY_PRO_SCORE_FORMULA = "0.75*normalized_role_pick_rate + 0.25*normalized_role_adjusted_ban_rate"
TEAMPLAY_BAN_CREDIT_MODE = "role_adjusted_v1"
TEAMPLAY_ELIGIBILITY_RULE = "solo_pool && pro_pick_count>0 && (pro_pick_count+pro_ban_count)>=5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build static Flex / Clash teamplay datasets.")
    parser.add_argument("--oe-csv", required=True, help="Local Oracle's Elixir CSV file path.")
    parser.add_argument("--solo-root", default="apps/web/public/data")
    parser.add_argument("--output-root", default="apps/web/public/data/teamplay")
    parser.add_argument("--regions", nargs="+", default=SUPPORTED_REGIONS, choices=SUPPORTED_REGIONS)
    parser.add_argument("--tiers", nargs="+", default=SUPPORTED_TIERS, choices=SUPPORTED_TIERS)
    parser.add_argument("--windows", nargs="+", default=SUPPORTED_WINDOWS, choices=SUPPORTED_WINDOWS)
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def safe_round(value: Any, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def clamp_ratio(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, min(value / maximum, 1.0))


def compute_solo_strength_score(filtered_rank: int, lane_count: int) -> float:
    if lane_count <= 1:
        return 1.0
    return 1 - ((filtered_rank - 1) / (lane_count - 1))


def build_badges(
    *,
    solo_strength_score: float,
    pro_score: float,
    normalized_role_adjusted_ban_rate: float,
    pro_flex_roles: int,
) -> List[str]:
    badges: List[str] = []
    if pro_score >= 0.75:
        badges.append(BADGE_HIGH_PRO_PRESENCE)
    if normalized_role_adjusted_ban_rate >= 0.6:
        badges.append(BADGE_DRAFT_PRIORITY)
    if pro_flex_roles >= 2:
        badges.append(BADGE_FLEX_PICK)
    if solo_strength_score >= 0.85:
        badges.append(BADGE_STRONG_IN_SOLO)
    return badges


def build_teamplay_champion(
    solo_champion: Dict[str, Any],
    *,
    lane: str,
    lane_count: int,
    role_stats: OracleRoleStats | None,
    champion_stats: OracleChampionStats | None,
    lane_max_role_pick_rate: float,
    lane_max_role_adjusted_ban_rate: float,
) -> Dict[str, Any]:
    champion = dict(solo_champion)
    filtered_rank = int(champion.get("filtered_rank") or lane_count or 1)
    solo_strength_score = compute_solo_strength_score(filtered_rank, lane_count)

    pro_pick_count = role_stats.pro_pick_count if role_stats else 0
    pro_role_pick_rate = role_stats.pro_role_pick_rate if role_stats else 0.0
    role_pick_share = role_stats.role_pick_share if role_stats else 0.0
    role_adjusted_ban_rate = role_stats.role_adjusted_ban_rate if role_stats else 0.0
    pro_win_rate = role_stats.pro_win_rate if role_stats else None
    pro_ban_count = champion_stats.pro_ban_count if champion_stats else 0
    pro_ban_rate = champion_stats.pro_ban_rate if champion_stats else 0.0
    pro_flex_roles = champion_stats.pro_flex_roles if champion_stats else 0
    champion_total_role_picks = champion_stats.champion_total_role_picks if champion_stats else 0

    normalized_role_pick_rate = clamp_ratio(pro_role_pick_rate, lane_max_role_pick_rate)
    normalized_role_adjusted_ban_rate = clamp_ratio(role_adjusted_ban_rate, lane_max_role_adjusted_ban_rate)
    pro_score = (0.75 * normalized_role_pick_rate) + (0.25 * normalized_role_adjusted_ban_rate)
    flex_clash_score = (0.90 * pro_score) + (0.10 * solo_strength_score)

    champion.update(
        {
            "lane": lane,
            "solo_strength_score": safe_round(solo_strength_score),
            "pro_pick_count": pro_pick_count,
            "pro_role_pick_rate": safe_round(pro_role_pick_rate),
            "pro_ban_count": pro_ban_count,
            "pro_ban_rate": safe_round(pro_ban_rate),
            "champion_total_role_picks": champion_total_role_picks,
            "role_pick_share": safe_round(role_pick_share),
            "role_adjusted_ban_rate": safe_round(role_adjusted_ban_rate),
            "pro_win_rate": safe_round(pro_win_rate),
            "pro_score": safe_round(pro_score),
            "flex_clash_score": safe_round(flex_clash_score),
            "pro_flex_roles": pro_flex_roles,
            "badges": build_badges(
                solo_strength_score=solo_strength_score,
                pro_score=pro_score,
                normalized_role_adjusted_ban_rate=normalized_role_adjusted_ban_rate,
                pro_flex_roles=pro_flex_roles,
            ),
        }
    )
    return champion


def is_teamplay_eligible(champion: Dict[str, Any]) -> bool:
    pro_pick_count = int(champion.get("pro_pick_count") or 0)
    pro_ban_count = int(champion.get("pro_ban_count") or 0)
    return pro_pick_count > 0 and (pro_pick_count + pro_ban_count) >= 5


def build_teamplay_dataset(
    *,
    solo_dataset: Dict[str, Any],
    pro_snapshot: OracleTeamplaySnapshot,
    region: str,
    tier: str,
    window: str,
) -> Dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).isoformat()
    solo_meta = solo_dataset.get("meta", {}) if isinstance(solo_dataset, dict) else {}
    solo_data = solo_dataset.get("data", {}) if isinstance(solo_dataset, dict) else {}

    combined_warnings = list(solo_meta.get("warnings", [])) + list(pro_snapshot.warnings)
    if solo_meta.get("is_partial"):
        combined_warnings.append("Solo source dataset is partial; teamplay rankings were blended from partial solo data.")

    teamplay_data: Dict[str, List[Dict[str, Any]]] = {}
    excluded_zero_pro_count = 0
    excluded_low_evidence_count = 0

    for lane in DEFAULT_LANES:
        solo_champions = solo_data.get(lane, [])
        if not isinstance(solo_champions, list):
            solo_champions = []

        lane_count = len(solo_champions)
        teamplay_champions: List[Dict[str, Any]] = []

        for solo_champion in solo_champions:
            if not isinstance(solo_champion, dict):
                continue

            champion_key = normalize_champion_key(str(solo_champion.get("name", "")))
            role_stats = pro_snapshot.role_stats.get((champion_key, lane))
            champion_stats = pro_snapshot.champion_stats.get(champion_key)
            teamplay_champions.append(
                build_teamplay_champion(
                    solo_champion,
                    lane=lane,
                    lane_count=lane_count,
                    role_stats=role_stats,
                    champion_stats=champion_stats,
                    lane_max_role_pick_rate=pro_snapshot.lane_max_role_pick_rate.get(lane, 0.0),
                    lane_max_role_adjusted_ban_rate=pro_snapshot.lane_max_role_adjusted_ban_rate.get(lane, 0.0),
                )
            )

        zero_pro_count = len(
            [
                champion
                for champion in teamplay_champions
                if (champion.get("pro_pick_count") or 0) == 0 and (champion.get("pro_ban_count") or 0) == 0
            ]
        )
        low_evidence_count = len([champion for champion in teamplay_champions if not is_teamplay_eligible(champion)])
        if low_evidence_count:
            teamplay_champions = [champion for champion in teamplay_champions if is_teamplay_eligible(champion)]
            excluded_low_evidence_count += low_evidence_count
        if zero_pro_count:
            excluded_zero_pro_count += zero_pro_count

        teamplay_champions.sort(
            key=lambda champion: (
                -(champion.get("flex_clash_score") or 0.0),
                -(champion.get("pro_score") or 0.0),
                champion.get("filtered_rank") or 9999,
                champion.get("name") or "",
            )
        )

        for idx, champion in enumerate(teamplay_champions, start=1):
            champion["teamplay_rank"] = idx

        teamplay_data[lane] = teamplay_champions

    meta = dict(solo_meta) if isinstance(solo_meta, dict) else {}
    meta.update(
        {
            "mode": "teamplay",
            "source": "Oracle's Elixir + LoLalytics",
            "region": region,
            "tier": tier,
            "window": window,
            "generated_at_utc": generated_at_utc,
            "leagues_used": list(pro_snapshot.leagues_used),
            "patches_used": list(pro_snapshot.patches_used),
            "total_games_filtered": pro_snapshot.total_games_filtered,
            "is_partial": bool(solo_meta.get("is_partial")) or pro_snapshot.is_partial,
            "failed_lanes": list(solo_meta.get("failed_lanes", [])),
            "warnings": list(dict.fromkeys(combined_warnings)),
            "rank_mode": TEAMPLAY_RANK_MODE,
            "inclusion_mode": STRICT_PRO_EVIDENCE_MODE,
            "excluded_zero_pro_count": excluded_zero_pro_count,
            "excluded_low_evidence_count": excluded_low_evidence_count,
            "score_formula": TEAMPLAY_SCORE_FORMULA,
            "pro_score_formula": TEAMPLAY_PRO_SCORE_FORMULA,
            "ban_credit_mode": TEAMPLAY_BAN_CREDIT_MODE,
            "eligibility_rule": TEAMPLAY_ELIGIBILITY_RULE,
        }
    )

    return {
        "meta": meta,
        "data": teamplay_data,
    }


def write_teamplay_dataset(output_path: Path, payload: Dict[str, Any]) -> None:
    existing_dataset = load_existing_dataset(output_path)
    is_partial = is_partial_dataset(payload)

    if is_partial and existing_dataset and not is_partial_dataset(existing_dataset):
        update_last_success_backup(output_path, existing_dataset)

    write_json(output_path, payload)

    if not is_partial:
        update_last_success_backup(output_path, payload)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    oe_csv = Path(args.oe_csv).resolve()
    solo_root = Path(args.solo_root).resolve()
    output_root = Path(args.output_root).resolve()
    manifest_path = solo_root / "manifest.json"

    try:
        output_root_rel = output_root.relative_to(solo_root)
    except ValueError as exc:
        raise ValueError(f"output-root must live under solo-root so manifest paths stay under /data: {output_root}") from exc
    if not output_root_rel.parts or output_root_rel.parts[0] != "teamplay":
        raise ValueError(f"output-root must be under a /teamplay subtree for manifest discovery: {output_root}")

    pro_snapshot = load_oracle_teamplay_snapshot(oe_csv, leagues=TEAMPLAY_LEAGUES)
    datasets: List[Dict[str, Any]] = []

    for region in args.regions:
        for tier in args.tiers:
            for window in args.windows:
                rel_path = output_root_rel / region / tier / f"{window}.json"
                output_path = output_root / region / tier / f"{window}.json"
                solo_path = solo_root / region / tier / f"{window}.json"

                entry: Dict[str, Any] = {
                    "mode": "teamplay",
                    "region": region,
                    "tier": tier,
                    "window": window,
                    "path": f"/data/{rel_path.as_posix()}",
                    "status": "ok",
                    "generated_at_utc": None,
                    "is_partial": False,
                    "failed_lanes": [],
                    "warnings": [],
                    "champion_count": 0,
                }

                print(f"[INFO] Building teamplay dataset region={region} tier={tier} window={window}")

                try:
                    solo_dataset = load_existing_dataset(solo_path)
                    if not solo_dataset:
                        raise FileNotFoundError(f"Solo dataset not found: {solo_path}")

                    result = build_teamplay_dataset(
                        solo_dataset=solo_dataset,
                        pro_snapshot=pro_snapshot,
                        region=region,
                        tier=tier,
                        window=window,
                    )
                    write_teamplay_dataset(output_path, result)

                    meta = result.get("meta", {})
                    entry["generated_at_utc"] = meta.get("generated_at_utc")
                    entry["is_partial"] = bool(meta.get("is_partial"))
                    entry["failed_lanes"] = list(meta.get("failed_lanes", []))
                    entry["warnings"] = list(meta.get("warnings", []))
                    entry["champion_count"] = count_champions(result.get("data", {}))
                    if entry["is_partial"]:
                        entry["status"] = "partial"

                    total = count_champions(result.get("data", {}))
                    print(f"[DONE] Wrote {total} teamplay champions to {output_path}")
                except Exception as exc:  # noqa: BLE001
                    entry["status"] = "error"
                    entry["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
                    entry["is_partial"] = True
                    entry["warnings"] = [f"Teamplay dataset generation failed: {exc}"]
                    entry["error"] = str(exc)
                    print(f"[ERROR] Failed teamplay region={region} tier={tier} window={window}: {exc}")
                    if args.fail_fast:
                        raise

                datasets.append(entry)

    existing_manifest = load_manifest(manifest_path)
    manifest = merge_manifest(
        existing_manifest=existing_manifest,
        new_entries=datasets,
        regions=list(args.regions),
        tiers=list(args.tiers),
        windows=list(args.windows),
        lanes=list(DEFAULT_LANES),
        modes=["teamplay"],
    )
    write_manifest(manifest_path, manifest)
    print(f"[DONE] Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TEAMPLAY_LEAGUES = ["LCK", "LPL", "LEC", "LCS"]
ORACLE_POSITION_TO_LANE = {
    "top": "top",
    "jng": "jungle",
    "mid": "middle",
    "bot": "bottom",
    "sup": "support",
}
BAN_FIELDS = ["ban1", "ban2", "ban3", "ban4", "ban5"]
FLEX_ROLE_MIN_PICK_COUNT = 3


@dataclass(slots=True)
class OracleRoleStats:
    pro_pick_count: int
    pro_role_pick_rate: float
    pro_win_count: int
    pro_win_rate: Optional[float]
    pro_role_games: int
    role_pick_share: float
    role_adjusted_ban_rate: float


@dataclass(slots=True)
class OracleChampionStats:
    pro_ban_count: int
    pro_ban_rate: float
    pro_flex_roles: int
    champion_total_role_picks: int


@dataclass(slots=True)
class OracleTeamplaySnapshot:
    leagues_used: List[str]
    patches_used: List[str]
    total_games_filtered: int
    role_stats: Dict[Tuple[str, str], OracleRoleStats]
    champion_stats: Dict[str, OracleChampionStats]
    lane_max_role_pick_rate: Dict[str, float]
    lane_max_role_adjusted_ban_rate: Dict[str, float]
    global_max_ban_rate: float
    is_partial: bool
    warnings: List[str]
    duplicate_pick_rows_skipped: int
    duplicate_bans_skipped: int


def normalize_champion_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_patch_key(value: str) -> Tuple[int, ...]:
    try:
        return tuple(int(part) for part in value.split("."))
    except ValueError:
        return (0,)


def parse_result_flag(value: str) -> Optional[int]:
    cleaned = clean_text(value)
    if cleaned in {"0", "1"}:
        return int(cleaned)
    return None


def select_latest_patches(
    csv_path: Path,
    *,
    leagues: List[str],
    patch_count: int = 3,
) -> List[str]:
    allowed_leagues = set(leagues)
    patches = set()

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            patch = clean_text(row.get("patch", ""))
            if clean_text(row.get("league", "")) not in allowed_leagues or not patch:
                continue
            patches.add(patch)

    return sorted(patches, key=parse_patch_key)[-patch_count:]


def load_oracle_teamplay_snapshot(
    csv_path: Path,
    *,
    leagues: List[str] | None = None,
    patch_count: int = 3,
) -> OracleTeamplaySnapshot:
    leagues_used = list(leagues or TEAMPLAY_LEAGUES)
    patches_used = select_latest_patches(csv_path, leagues=leagues_used, patch_count=patch_count)
    if not patches_used:
        raise ValueError(f"No Oracle patches found in {csv_path} for leagues={leagues_used}")

    allowed_leagues = set(leagues_used)
    allowed_patches = set(patches_used)

    games_filtered = set()
    pick_slot_seen = set()
    ban_seen = set()
    pick_counts: Counter[Tuple[str, str]] = Counter()
    win_counts: Counter[Tuple[str, str]] = Counter()
    ban_counts: Counter[str] = Counter()
    champion_roles: defaultdict[str, Dict[str, int]] = defaultdict(dict)

    duplicate_pick_rows_skipped = 0
    duplicate_bans_skipped = 0
    is_partial = False
    warnings: List[str] = []

    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            league = clean_text(row.get("league", ""))
            patch = clean_text(row.get("patch", ""))
            if league not in allowed_leagues or patch not in allowed_patches:
                continue

            gameid = clean_text(row.get("gameid", ""))
            if not gameid:
                continue

            games_filtered.add(gameid)

            completeness = clean_text(row.get("datacompleteness", "")).lower()
            if completeness and completeness != "complete":
                is_partial = True

            position = clean_text(row.get("position", "")).lower()
            if position in ORACLE_POSITION_TO_LANE:
                side = clean_text(row.get("side", "")).lower()
                dedupe_key = (gameid, side, position)
                if dedupe_key in pick_slot_seen:
                    duplicate_pick_rows_skipped += 1
                    continue

                pick_slot_seen.add(dedupe_key)

                champion_name = clean_text(row.get("champion", ""))
                if not champion_name:
                    continue

                champion_key = normalize_champion_key(champion_name)
                lane = ORACLE_POSITION_TO_LANE[position]
                key = (champion_key, lane)

                pick_counts[key] += 1
                champion_roles[champion_key][lane] = pick_counts[key]

                result = parse_result_flag(row.get("result", ""))
                if result == 1:
                    win_counts[key] += 1

            if position == "team":
                for field in BAN_FIELDS:
                    champion_name = clean_text(row.get(field, ""))
                    if not champion_name:
                        continue

                    champion_key = normalize_champion_key(champion_name)
                    dedupe_key = (gameid, champion_key)
                    if dedupe_key in ban_seen:
                        duplicate_bans_skipped += 1
                        continue

                    ban_seen.add(dedupe_key)
                    ban_counts[champion_key] += 1

    total_games_filtered = len(games_filtered)
    if total_games_filtered == 0:
        raise ValueError(f"No Oracle games remained after filtering leagues={leagues_used} patches={patches_used}")

    champion_stats: Dict[str, OracleChampionStats] = {}
    global_max_ban_rate = 0.0
    champion_keys = set(ban_counts) | {champion_key for champion_key, _ in pick_counts}

    for champion_key in champion_keys:
        ban_count = ban_counts.get(champion_key, 0)
        ban_rate = ban_count / total_games_filtered
        champion_total_role_picks = sum(champion_roles.get(champion_key, {}).values())
        flex_role_count = sum(
            1 for pick_count in champion_roles.get(champion_key, {}).values() if pick_count >= FLEX_ROLE_MIN_PICK_COUNT
        )
        champion_stats[champion_key] = OracleChampionStats(
            pro_ban_count=ban_count,
            pro_ban_rate=ban_rate,
            pro_flex_roles=flex_role_count,
            champion_total_role_picks=champion_total_role_picks,
        )
        global_max_ban_rate = max(global_max_ban_rate, ban_rate)

    role_stats: Dict[Tuple[str, str], OracleRoleStats] = {}
    lane_max_role_pick_rate = {lane: 0.0 for lane in ORACLE_POSITION_TO_LANE.values()}
    lane_max_role_adjusted_ban_rate = {lane: 0.0 for lane in ORACLE_POSITION_TO_LANE.values()}

    for key, pick_count in pick_counts.items():
        champion_key, lane = key
        role_pick_rate = pick_count / (2 * total_games_filtered)
        win_count = win_counts.get(key, 0)
        win_rate = (win_count / pick_count) if pick_count else None
        champion_stat = champion_stats.get(champion_key)
        champion_total_role_picks = champion_stat.champion_total_role_picks if champion_stat else 0
        role_pick_share = (pick_count / champion_total_role_picks) if champion_total_role_picks > 0 else 0.0
        role_adjusted_ban_rate = (champion_stat.pro_ban_rate if champion_stat else 0.0) * role_pick_share

        role_stats[key] = OracleRoleStats(
            pro_pick_count=pick_count,
            pro_role_pick_rate=role_pick_rate,
            pro_win_count=win_count,
            pro_win_rate=win_rate,
            pro_role_games=pick_count,
            role_pick_share=role_pick_share,
            role_adjusted_ban_rate=role_adjusted_ban_rate,
        )
        lane_max_role_pick_rate[lane] = max(lane_max_role_pick_rate[lane], role_pick_rate)
        lane_max_role_adjusted_ban_rate[lane] = max(
            lane_max_role_adjusted_ban_rate[lane],
            role_adjusted_ban_rate,
        )

    if len(patches_used) < patch_count:
        warnings.append(
            f"Oracle competitive slice only had {len(patches_used)} patch values available; requested {patch_count}."
        )
    if is_partial:
        warnings.append("Oracle competitive slice includes rows where datacompleteness != 'complete'.")
    if duplicate_pick_rows_skipped:
        warnings.append(
            "Skipped "
            f"{duplicate_pick_rows_skipped} duplicate player rows after dedupe on gameid + side + position."
        )
    if duplicate_bans_skipped:
        warnings.append(
            "Skipped "
            f"{duplicate_bans_skipped} duplicate bans after dedupe on gameid + banned_champion."
        )

    return OracleTeamplaySnapshot(
        leagues_used=leagues_used,
        patches_used=patches_used,
        total_games_filtered=total_games_filtered,
        role_stats=role_stats,
        champion_stats=champion_stats,
        lane_max_role_pick_rate=lane_max_role_pick_rate,
        lane_max_role_adjusted_ban_rate=lane_max_role_adjusted_ban_rate,
        global_max_ban_rate=global_max_ban_rate,
        is_partial=is_partial,
        warnings=list(dict.fromkeys(warnings)),
        duplicate_pick_rows_skipped=duplicate_pick_rows_skipped,
        duplicate_bans_skipped=duplicate_bans_skipped,
    )

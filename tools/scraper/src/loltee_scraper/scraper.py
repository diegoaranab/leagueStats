from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import BrowserContext
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .config import DEFAULT_LANES, SUPPORTED_WINDOWS, WINDOW_PATCH_QUERY_VALUES, normalize_lanes

BASE_URL = "https://lolalytics.com/lol/tierlist/"
ALLOWED_TIERS = {"S+", "S", "S-", "A+", "A", "A-", "B+"}
DIFFICULTY_COLORS = {"easy": "#5BC0FF", "medium": "#FFD54F", "hard": "#FF5A5F"}
DIFFICULTY_ORDER = {"easy": 1, "medium": 2, "hard": 3}
DIFFICULTY_METHOD = "lane_relative_mastery_gap_pct_tertiles_v1"
LANE_RETRY_BACKOFF_SECONDS = (0, 2, 5)


@dataclass(slots=True)
class ScrapeConfig:
    region: str = "na"
    tier: str = "diamond_plus"
    window: str = "7d"
    lanes: List[str] = field(default_factory=lambda: DEFAULT_LANES.copy())
    output_path: Optional[Path] = None

    def validated(self) -> "ScrapeConfig":
        return ScrapeConfig(
            region=self.region,
            tier=self.tier,
            window=self.window,
            lanes=normalize_lanes(self.lanes),
            output_path=self.output_path,
        )


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_float(text: str) -> Optional[float]:
    text = clean_text(text).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(text: str) -> Optional[int]:
    text = clean_text(text).replace(",", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def safe_round(value: Any, digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, digits)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_existing_dataset(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Failed to load existing dataset {path}: {exc}")
        return None

    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def build_last_success_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.last_success{path.suffix}")


def update_last_success_backup(path: Path, payload: Dict[str, Any]) -> None:
    backup_path = build_last_success_path(path)
    write_json(backup_path, payload)
    print(f"[INFO] Updated last-success backup: {backup_path}")


def is_partial_dataset(payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(payload, dict):
        return False

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return False

    return bool(meta.get("is_partial"))


def count_champions(data: Any) -> int:
    if not isinstance(data, dict):
        return 0

    return sum(len(champions) for champions in data.values() if isinstance(champions, list))


def build_dataset_meta(
    *,
    config: ScrapeConfig,
    generated_at_utc: str,
    failed_lanes: List[str],
    warnings: List[str],
) -> Dict[str, Any]:
    return {
        "source": "LoLalytics",
        "region": config.region,
        "tier": config.tier,
        "window": config.window,
        "min_pick_rate": 1.0,
        "allowed_tiers": sorted(ALLOWED_TIERS),
        "generated_at_utc": generated_at_utc,
        "is_partial": bool(failed_lanes),
        "failed_lanes": failed_lanes,
        "warnings": warnings,
    }


def get_direct_child_divs(tag: Tag) -> List[Tag]:
    return [child for child in tag.children if isinstance(child, Tag) and child.name == "div"]


def build_tierlist_url(*, lane: str, tier: str, region: str, window: str) -> str:
    patch = WINDOW_PATCH_QUERY_VALUES.get(window, WINDOW_PATCH_QUERY_VALUES["7d"])
    params = {
        "lane": lane,
        "tier": tier,
        "region": region,
    }
    if patch is not None:
        params["patch"] = patch
    return f"{BASE_URL}?{urlencode(params)}"


def build_lane_url(lane: str, config: ScrapeConfig) -> str:
    return build_tierlist_url(
        lane=lane,
        tier=config.tier,
        region=config.region,
        window=config.window,
    )


def build_window_url_smoke_samples(
    lane: str = "middle",
    tier: str = "diamond_plus",
    region: str = "na",
) -> Dict[str, str]:
    return {
        window: build_tierlist_url(lane=lane, tier=tier, region=region, window=window)
        for window in SUPPORTED_WINDOWS
    }


def validate_window_url_builder() -> None:
    expected = {
        "current": "https://lolalytics.com/lol/tierlist/?lane=middle&tier=diamond_plus&region=na",
        "7d": "https://lolalytics.com/lol/tierlist/?lane=middle&tier=diamond_plus&region=na&patch=7",
        "14d": "https://lolalytics.com/lol/tierlist/?lane=middle&tier=diamond_plus&region=na&patch=14",
    }
    actual = build_window_url_smoke_samples()
    if actual != expected:
        raise AssertionError(f"Unexpected tierlist URL mapping: {actual}")


def scroll_until_stable(
    page,
    step_px: int = 700,
    wait_ms: int = 700,
    max_rounds: int = 200,
    stable_rounds: int = 5,
) -> None:
    """
    LoLalytics tierlist lazy-loads additional rows as you approach the bottom.
    Incremental scrolling is more reliable than jumping directly to the end once.
    """
    stable = 0

    for _ in range(max_rounds):
        at_bottom = page.evaluate(
            """
            () => {
              const y = window.scrollY || window.pageYOffset;
              const h = window.innerHeight;
              const doc = document.body.scrollHeight;
              return y + h >= doc - 4;
            }
            """
        )
        if at_bottom:
            stable += 1
        else:
            stable = 0

        if stable >= stable_rounds:
            break

        page.evaluate(f"window.scrollBy(0, {step_px})")
        page.wait_for_timeout(wait_ms)


def is_candidate_row(tag: Tag) -> bool:
    if tag.name != "div":
        return False

    classes = tag.get("class", [])
    if not isinstance(classes, list):
        return False

    # Real data rows have these classes on LoLalytics at the moment.
    if "flex" not in classes or "justify-between" not in classes or "h-[52px]" not in classes:
        return False

    build_link = tag.find("a", href=re.compile(r"^/lol/[^/]+/build/"))
    if not build_link:
        return False

    cells = get_direct_child_divs(tag)
    return len(cells) >= 14


def extract_icon_url(cell: Tag) -> Optional[str]:
    img = cell.find("img", src=re.compile(r"/champx\d+/"))
    if img and img.get("src"):
        return img["src"]
    return None


def extract_champion_url(cell: Tag) -> Optional[str]:
    link = cell.find("a", href=re.compile(r"^/lol/[^/]+/build/"))
    if link and link.get("href"):
        return "https://lolalytics.com" + link["href"]
    return None


def extract_win_block(cell: Tag) -> tuple[Optional[float], Optional[float]]:
    text = cell.get_text(" ", strip=True).replace(",", "")
    nums = re.findall(r"[+-]?\d+(?:\.\d+)?", text)

    if not nums:
        return None, None

    win_rate = float(nums[0])
    win_delta = float(nums[1]) if len(nums) > 1 else None
    return win_rate, win_delta


def extract_row(row: Tag, lane: str) -> Optional[Dict[str, Any]]:
    cells = get_direct_child_divs(row)
    if len(cells) < 14:
        return None

    rank = parse_int(cells[0].get_text(" ", strip=True))
    icon_url = extract_icon_url(cells[1])
    champion_url = extract_champion_url(cells[2]) or extract_champion_url(cells[1])
    name = clean_text(cells[2].get_text(" ", strip=True))
    tier = clean_text(cells[3].get_text(" ", strip=True))

    win_rate, win_delta = extract_win_block(cells[5])
    pick_rate = parse_float(cells[6].get_text(" ", strip=True))
    ban_rate = parse_float(cells[7].get_text(" ", strip=True))
    pbi = parse_int(cells[8].get_text(" ", strip=True))
    delta = parse_float(cells[13].get_text(" ", strip=True))

    if not name or tier not in ALLOWED_TIERS:
        return None

    if pick_rate is None or pick_rate < 1.0:
        return None

    return {
        "lane": lane,
        "rank": rank,
        "name": name,
        "icon_url": icon_url,
        "champion_url": champion_url,
        "tier": tier,
        "win_rate": win_rate,
        "win_delta": win_delta,
        "pick_rate": pick_rate,
        "ban_rate": ban_rate,
        "pbi": pbi,
        "delta": delta,
    }


def parse_lane_html(html: str, lane: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")

    results: List[Dict[str, Any]] = []
    seen = set()

    for row in soup.find_all(is_candidate_row):
        item = extract_row(row, lane)
        if not item:
            continue

        key = (item["lane"], item["name"])
        if key in seen:
            continue

        seen.add(key)
        results.append(item)

    results.sort(key=lambda x: (x["rank"] is None, x["rank"]))
    return results


def format_scrape_error(exc: Exception) -> str:
    message = clean_text(str(exc))
    if message:
        return message
    return exc.__class__.__name__


def scrape_lane(page, lane: str, config: ScrapeConfig) -> List[Dict[str, Any]]:
    url = build_lane_url(lane, config)
    print(f"[INFO] Scraping {lane}: {url}")

    page.goto(url, wait_until="domcontentloaded", timeout=45000)

    page.wait_for_function(
        """
        () => document.querySelectorAll('a[href^="/lol/"][href*="/build/"]').length > 0
        """,
        timeout=20000,
    )

    page.wait_for_timeout(1200)
    scroll_until_stable(page)

    html = page.content()
    rows = parse_lane_html(html, lane)

    print(f"[INFO] {lane}: extracted {len(rows)} champions after filters")
    return rows


def scrape_lane_with_retry(
    context: BrowserContext,
    lane: str,
    config: ScrapeConfig,
    max_attempts: int = 3,
) -> tuple[List[Dict[str, Any]], List[str], bool]:
    warnings: List[str] = []
    attempts = min(max_attempts, len(LANE_RETRY_BACKOFF_SECONDS))
    last_error: Optional[str] = None

    for attempt in range(1, attempts + 1):
        backoff_seconds = LANE_RETRY_BACKOFF_SECONDS[attempt - 1]
        if backoff_seconds > 0:
            print(
                f"[WARN] Retrying lane={lane} "
                f"region={config.region} tier={config.tier} window={config.window} "
                f"attempt={attempt}/{attempts} after {backoff_seconds}s"
            )
            time.sleep(backoff_seconds)

        print(
            f"[INFO] Lane attempt {attempt}/{attempts} "
            f"region={config.region} tier={config.tier} window={config.window} lane={lane}"
        )

        page = None
        try:
            page = context.new_page()
            rows = scrape_lane(page, lane, config)
            if attempt > 1:
                warnings.append(f"Lane {lane} succeeded on retry attempt {attempt}/{attempts}.")
            return rows, warnings, True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            last_error = format_scrape_error(exc)
            print(
                f"[WARN] Lane scrape failed "
                f"region={config.region} tier={config.tier} window={config.window} "
                f"lane={lane} attempt={attempt}/{attempts}: {last_error}"
            )
        finally:
            if page is not None and not page.is_closed():
                page.close()

    failure_reason = last_error or "unknown Playwright error"
    warnings.append(f"Lane {lane} failed after {attempts} attempts: {failure_reason}")
    return [], warnings, False


def scrape_all_lanes(config: ScrapeConfig, headless: bool = True) -> Dict[str, Any]:
    config = config.validated()
    data: Dict[str, List[Dict[str, Any]]] = {}
    failed_lanes: List[str] = []
    warnings: List[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1600, "height": 2200},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        for lane in config.lanes:
            try:
                lane_data, lane_warnings, succeeded = scrape_lane_with_retry(context, lane, config)
                data[lane] = lane_data
                warnings.extend(lane_warnings)
                if not succeeded:
                    failed_lanes.append(lane)
            except Exception as exc:  # noqa: BLE001
                error_message = format_scrape_error(exc)
                print(
                    f"[ERROR] Unexpected lane failure "
                    f"region={config.region} tier={config.tier} window={config.window} "
                    f"lane={lane}: {error_message}"
                )
                data[lane] = []
                failed_lanes.append(lane)
                warnings.append(f"Lane {lane} failed due to unexpected scraper error: {error_message}")

        warnings = list(dict.fromkeys(warnings))

        context.close()
        browser.close()

    generated_at_utc = datetime.now(timezone.utc).isoformat()
    return {
        "meta": build_dataset_meta(
            config=config,
            generated_at_utc=generated_at_utc,
            failed_lanes=failed_lanes,
            warnings=warnings,
        ),
        "data": data,
    }


def add_filtered_ranks(champions: List[Dict[str, Any]]) -> None:
    for idx, champion in enumerate(champions, start=1):
        champion["filtered_rank"] = idx


def compute_mastery_fields(champion: Dict[str, Any]) -> None:
    champion["best_win_est"] = None
    champion["mastery_gap_raw"] = None
    champion["mastery_gap_pct"] = None

    win_rate = champion.get("win_rate")
    delta = champion.get("delta")
    if win_rate is None or delta is None:
        return

    try:
        win_rate_value = float(win_rate)
        delta_value = float(delta)
    except (TypeError, ValueError):
        return

    best_win_est = safe_round(win_rate_value + delta_value)
    mastery_gap_raw = safe_round(max(delta_value, 0.0))

    champion["best_win_est"] = best_win_est
    champion["mastery_gap_raw"] = mastery_gap_raw

    if best_win_est is None or mastery_gap_raw is None or best_win_est <= 0:
        return

    champion["mastery_gap_pct"] = safe_round((mastery_gap_raw / best_win_est) * 100)


def assign_lane_difficulty(champions: List[Dict[str, Any]]) -> None:
    for champion in champions:
        champion["difficulty"] = None
        champion["difficulty_color"] = None
        champion["difficulty_order"] = None

    eligible = [
        champion
        for champion in champions
        if isinstance(champion.get("mastery_gap_pct"), (int, float))
    ]
    if not eligible:
        return

    eligible.sort(
        key=lambda c: (
            c["mastery_gap_pct"],
            c.get("rank") is None,
            c.get("rank") if c.get("rank") is not None else float("inf"),
            c.get("name", ""),
        )
    )

    total = len(eligible)
    easy_cut = (total + 2) // 3
    medium_cut = (2 * total + 2) // 3

    for idx, champion in enumerate(eligible):
        if idx < easy_cut:
            difficulty = "easy"
        elif idx < medium_cut:
            difficulty = "medium"
        else:
            difficulty = "hard"

        champion["difficulty"] = difficulty
        champion["difficulty_color"] = DIFFICULTY_COLORS[difficulty]
        champion["difficulty_order"] = DIFFICULTY_ORDER[difficulty]


def post_process_data(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {})
    if isinstance(data, dict):
        for champions in data.values():
            if not isinstance(champions, list):
                continue
            add_filtered_ranks(champions)
            for champion in champions:
                if isinstance(champion, dict):
                    compute_mastery_fields(champion)
            assign_lane_difficulty(champions)

    meta = result.get("meta")
    if isinstance(meta, dict):
        meta["difficulty_method"] = DIFFICULTY_METHOD
        meta["rank_mode"] = "original_rank_plus_filtered_rank"
        meta["difficulty_colors"] = DIFFICULTY_COLORS

    return result


def default_output_path(config: ScrapeConfig) -> Path:
    return Path("apps/web/public/data") / config.region / config.tier / f"{config.window}.json"


def scrape_to_file(config: ScrapeConfig, headless: bool = True) -> Dict[str, Any]:
    config = config.validated()
    output = config.output_path or default_output_path(config)

    result = scrape_all_lanes(config=config, headless=headless)
    result = post_process_data(result)
    existing_dataset = load_existing_dataset(output)
    is_partial = is_partial_dataset(result)

    if is_partial and existing_dataset and not is_partial_dataset(existing_dataset):
        update_last_success_backup(output, existing_dataset)

    write_json(output, result)

    if not is_partial:
        update_last_success_backup(output, result)

    total = count_champions(result.get("data", {}))
    print(f"[DONE] Wrote {total} champions to {output}")
    return result

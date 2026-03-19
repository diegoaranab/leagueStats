from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .config import DEFAULT_LANES, SUPPORTED_REGIONS, SUPPORTED_TIERS, SUPPORTED_WINDOWS
from .scraper import ScrapeConfig, count_champions, scrape_to_file, write_json


def build_manifest(
    datasets: List[Dict[str, object]],
    regions: List[str],
    tiers: List[str],
    windows: List[str],
    lanes: List[str],
) -> Dict[str, object]:
    return {
        "meta": {
            "source": "loltee_scraper",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "supported": {
            "regions": regions,
            "tiers": tiers,
            "windows": windows,
            "lanes": lanes,
        },
        "datasets": datasets,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run scraper across region/tier/window matrix.")
    parser.add_argument("--output-root", default="apps/web/public/data")
    parser.add_argument("--regions", nargs="+", default=SUPPORTED_REGIONS, choices=SUPPORTED_REGIONS)
    parser.add_argument("--tiers", nargs="+", default=SUPPORTED_TIERS, choices=SUPPORTED_TIERS)
    parser.add_argument("--windows", nargs="+", default=SUPPORTED_WINDOWS, choices=SUPPORTED_WINDOWS)
    parser.add_argument("--lanes", nargs="+", default=DEFAULT_LANES, choices=DEFAULT_LANES)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    datasets: List[Dict[str, object]] = []

    for region in args.regions:
        for tier in args.tiers:
            for window in args.windows:
                rel_path = f"{region}/{tier}/{window}.json"
                output_path = output_root / rel_path

                print(f"[INFO] Running scrape for region={region} tier={tier} window={window}")
                entry: Dict[str, object] = {
                    "region": region,
                    "tier": tier,
                    "window": window,
                    "path": f"/data/{rel_path}",
                    "status": "ok",
                    "generated_at_utc": None,
                    "is_partial": False,
                    "failed_lanes": [],
                    "warnings": [],
                    "champion_count": 0,
                }

                try:
                    result = scrape_to_file(
                        config=ScrapeConfig(
                            region=region,
                            tier=tier,
                            window=window,
                            lanes=list(args.lanes),
                            output_path=output_path,
                        ),
                        headless=not args.headed,
                    )
                    meta = result.get("meta", {})
                    entry["generated_at_utc"] = meta.get("generated_at_utc")
                    entry["is_partial"] = bool(meta.get("is_partial"))
                    entry["failed_lanes"] = list(meta.get("failed_lanes", []))
                    entry["warnings"] = list(meta.get("warnings", []))
                    entry["champion_count"] = count_champions(result.get("data", {}))
                    if entry["is_partial"]:
                        entry["status"] = "partial"
                except Exception as exc:  # noqa: BLE001
                    entry["status"] = "error"
                    entry["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
                    entry["is_partial"] = True
                    entry["failed_lanes"] = list(args.lanes)
                    entry["warnings"] = [f"Dataset generation failed: {exc}"]
                    entry["error"] = str(exc)
                    print(f"[ERROR] Failed region={region} tier={tier} window={window}: {exc}")
                    if args.fail_fast:
                        raise

                datasets.append(entry)

    manifest_path = output_root / "manifest.json"
    manifest = build_manifest(
        datasets=datasets,
        regions=list(args.regions),
        tiers=list(args.tiers),
        windows=list(args.windows),
        lanes=list(args.lanes),
    )
    write_json(manifest_path, manifest)
    print(f"[DONE] Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_LANES, SUPPORTED_REGIONS, SUPPORTED_TIERS, SUPPORTED_WINDOWS
from .scraper import ScrapeConfig, scrape_to_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape LoLalytics tier list by lane.")
    parser.add_argument("--region", default="na", choices=SUPPORTED_REGIONS)
    parser.add_argument("--tier", default="diamond_plus", choices=SUPPORTED_TIERS)
    parser.add_argument("--window", default="7d", choices=SUPPORTED_WINDOWS)
    parser.add_argument(
        "--lanes",
        nargs="+",
        default=DEFAULT_LANES,
        choices=DEFAULT_LANES,
        help="One or more lanes to scrape.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path. Defaults to apps/web/public/data/{region}/{tier}/{window}.json",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window for debugging.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = ScrapeConfig(
        region=args.region,
        tier=args.tier,
        window=args.window,
        lanes=list(args.lanes),
        output_path=Path(args.output) if args.output else None,
    )

    scrape_to_file(config=config, headless=not args.headed)


if __name__ == "__main__":
    main()

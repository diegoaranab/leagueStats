from __future__ import annotations

__all__ = ["ScrapeConfig", "scrape_all_lanes", "scrape_to_file", "post_process_data"]


def __getattr__(name: str):
    if name in __all__:
        from .scraper import ScrapeConfig, post_process_data, scrape_all_lanes, scrape_to_file

        exports = {
            "ScrapeConfig": ScrapeConfig,
            "scrape_all_lanes": scrape_all_lanes,
            "scrape_to_file": scrape_to_file,
            "post_process_data": post_process_data,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

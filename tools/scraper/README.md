# Scraper

This package contains the LoLalytics scraping pipeline used to generate static JSON files for the Angular app.

## Install

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Single dataset

```bash
python -m loltee_scraper --region na --tier diamond --window 7d
```

## Full matrix + manifest

```bash
python -m loltee_scraper.run_matrix --output-root ../../apps/web/public/data
```

Outputs:

- `apps/web/public/data/{region}/{tier}/{window}.json`
- `apps/web/public/data/manifest.json`

### Teamplay denial priorities

`build_teamplay` also generates `teamplay_ban_score` and `teamplay_ban_rank` for
its existing eligible lane pools. Denial priority weights normalized role-adjusted
pro bans at 70%, normalized pro role picks at 20%, and Solo strength at 10%.
This is separate from the unchanged 90% pro / 10% Solo pick ranking.
See [the data schema](../../docs/DATA_SCHEMA.md#teamplay-recommended-bans) for
metadata and deterministic ordering. No full scrape is needed to test this feature:
`python3 -m unittest discover -s tools/scraper/tests -p 'test_teamplay_bans.py' -v`.

## Oracle CSV reliability validation

`loltee-oracle-download` resolves the 2026 Oracle's Elixir CSV through the
direct Google Drive URL, its alternate endpoint, and `gdown`, then falls back
to a validated cache or a known snapshot. Install its optional dependency with:

```bash
pip install -e "tools/scraper[oracle-download]"
```

Every candidate is downloaded to a temporary file and must pass schema, row,
year, timestamp, size, and content validation before an atomic replacement.
Cache metadata includes a SHA-256 checksum that is verified before reuse.

The JSON metadata uses these states:

- `FRESH`: a live source produced valid data whose latest match is within the
  configured Bet AI threshold.
- `CACHED`: a checksum-verified cache is within both the cache and Bet AI age
  thresholds.
- `STALE`: a valid source is available, but it is too old or is the historical
  snapshot.
- `FAILED`: no valid live, cached, or snapshot source exists.

`content_changed` and `is_recent_for_bet_ai` must be inspected independently;
a successful command does not by itself mean the upstream CSV was updated.
The isolated GitHub workflow `oracle-download-validation.yml` exposes this
validation only through `workflow_dispatch` and does not generate or publish
application data.

Phase 1B source investigation returned **NO-GO for fresh LoL Bet AI data**;
see [the evidence report](../../docs/bet-ai/phase-1b/README.md). The resolver's
24-hour latest-match threshold is a legacy eligibility heuristic, not proof
of an upstream update. The report specifies separate publisher, retrieval and
match clocks without changing this resolver or production workflows.

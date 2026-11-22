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

`loltee-oracle-download` retrieves the official 2026 CSV using authenticated
Google Drive API access. On failure it uses a validated, checksum-verified cache
whose original download is no older than the configured limit (48 hours in
production); otherwise it fails. Install with `pip install -e tools/scraper`.

Live downloads pass Drive size and MD5 checks and CSV validation before replacing
the output or refreshing the cache. Cache reuse preserves the original download
time. Result states are `FRESH`, `CACHED`, and `FAILED`. Download age controls
cache eligibility; latest-match age is observational and does not gate production.
`content_changed` reports whether the validated content differs from prior data.
The isolated GitHub workflow `oracle-download-validation.yml` exposes this
validation only through `workflow_dispatch` and does not generate or publish
application data.

# Architecture

## Goal

Serve champion recommendations without an always-on backend.

## System Design

1. `tools/scraper` scrapes LoLalytics by `region/tier/window/lane`.
2. Output JSON files are generated into `apps/web/public/data/...`.
3. Angular SPA reads those static files directly over HTTP.
4. GitHub Actions refreshes data on schedule and deploys SPA to GitHub Pages.

## Repository Structure

```text
repo-root/
  apps/web/
  tools/scraper/
  .github/workflows/
  docs/
  README.md
```

## Frontend Flow

1. User picks `Tu rango actual`, `Tu servidor`, `Ventana del meta`.
2. App routes to `/results` with query params:
   - `region`
   - `tier`
   - `window`
   - `lane`
   - `sort`
3. Results page loads static JSON from `/data/{region}/{tier}/{window}.json`.
4. Filters remain outside the champion card grid.
5. Champion card shows key stats first and advanced stats in expandable details.

## Scraper Flow

1. Build LoLalytics URL from `lane + region + tier + window`.
2. Load page with Playwright and scroll until stable.
3. Parse rows with BeautifulSoup.
4. Apply existing filters and post-processing:
   - min pick rate filter
   - allowed tiers filter
   - filtered rank
   - mastery-gap fields
   - lane-relative difficulty bins
5. Write JSON dataset and update manifest.

## Placeholder Decisions

- `window=current` query-to-LoLalytics mapping is a placeholder in `tools/scraper/src/loltee_scraper/config.py` and should be validated with real URLs.

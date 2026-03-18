# LolTEEEST

Static-first League of Legends web app that recommends champions by user context (`region`, `tier`, `window`) using pre-generated JSON.

## Monorepo Layout

- `apps/web`: Angular SPA + static data files
- `tools/scraper`: Python scraping package (Playwright + BeautifulSoup)
- `.github/workflows`: CI automation for scraping and GitHub Pages deploy
- `docs`: architecture, schema, roadmap

## Quick Start

### 1) Web app

```bash
cd apps/web
npm install
npm start
```

### 2) Scraper (single dataset)

```bash
pip install -e tools/scraper
python -m playwright install chromium
python -m loltee_scraper --region na --tier diamond_plus --window 7d
```

### 3) Scraper matrix + manifest

```bash
python -m loltee_scraper.run_matrix --output-root apps/web/public/data
```

## Data Convention

- Dataset path: `apps/web/public/data/{region}/{tier}/{window}.json`
- Manifest path: `apps/web/public/data/manifest.json`

## Supported (MVP)

- Regions: `na`, `lan`, `las`
- Tiers: `gold_plus`, `platinum_plus`, `emerald_plus`, `diamond_plus`, `d2_plus`, `master_plus`
- Windows: `current`, `7d`, `14d`

## Notes

- The scraper extraction and post-processing logic was migrated from your existing script and kept behavior-compatible for default values.
- `current` window uses a placeholder LoLalytics `patch` mapping in code and can be tuned after validation.

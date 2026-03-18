# Scraper

This package contains the LoLalytics scraping pipeline used to generate static JSON files for the Angular app.

## Install

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## Single dataset

```bash
python -m loltee_scraper --region na --tier diamond_plus --window 7d
```

## Full matrix + manifest

```bash
python -m loltee_scraper.run_matrix --output-root ../../apps/web/public/data
```

Outputs:

- `apps/web/public/data/{region}/{tier}/{window}.json`
- `apps/web/public/data/manifest.json`

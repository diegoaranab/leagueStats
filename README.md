# LeagueStats

LeagueStats is a static-first League of Legends recommendation app with two modes:
**Solo Queue** and **Flex / Clash**. An Angular SPA reads pre-generated JSON, without
an always-on backend.

## Modes

### Solo Queue

Uses LoLalytics ladder data to provide champion rankings, Easy / Medium / Hard
difficulty with Difficulty v2 historical smoothing, and Solo Recommended Bans
based on positive PBI.

### Flex / Clash

Blends Oracle's Elixir professional evidence with Solo strength. Teamplay v3
ranking asks **“What should we pick/value?”**, while Teamplay Recommended Bans ask
**“What should we deny?”**

```text
pro_score = 0.75 * normalized_role_pick_rate + 0.25 * normalized_role_adjusted_ban_rate
flex_clash_score = 0.90 * pro_score + 0.10 * solo_strength_score
teamplay_ban_score = 0.70 * normalized_role_adjusted_ban_rate + 0.20 * normalized_role_pick_rate + 0.10 * solo_strength_score
```

See [Data Schema](docs/DATA_SCHEMA.md#teamplay-recommended-bans) for role-specific
evidence, eligibility, and ranking details.

## Supported contexts

- Regions: `na`, `lan`, `las`
- Exact ranks: `iron`, `bronze`, `silver`, `gold`, `platinum`, `emerald`, `diamond`, `master`
- Windows: `current`, `7d`, `14d`
- Lanes: `top`, `jungle`, `middle`, `bottom`, `support`

The LoLalytics `current` window deliberately omits an explicit `patch` query
parameter; `7d` uses `patch=7` and `14d` uses `patch=14`.

## Quick start

Frontend:

```bash
cd apps/web
npm ci
npm start
```

Scraper environment (Python 3.11+, from the repository root; use a virtual environment):

```bash
python -m pip install -e tools/scraper
python -m playwright install chromium
```

Representative single Solo dataset, covering all five lanes:

```bash
python -m loltee_scraper --region na --tier diamond --window 7d
```

Generated datasets live under `apps/web/public/data/` and are intentionally
gitignored. The frontend needs generated data to display recommendations.
Solo files use `{region}/{tier}/{window}.json`, Teamplay files use
`teamplay/{region}/{tier}/{window}.json`, and `manifest.json` lists datasets.

## Repository layout and documentation

- `apps/web`: Angular SPA
- `tools/scraper`: Python scraper and Teamplay builder
- `.github/workflows`: PR validation and production generation/deployment
- [Architecture](docs/ARCHITECTURE.md): data flows and CI
- [Data Schema](docs/DATA_SCHEMA.md): dataset fields and Teamplay scoring
- [Difficulty v2 History](docs/DIFFICULTY_HISTORY.md): persistence and smoothing
- [Roadmap](docs/ROADMAP.md): implemented capabilities and future candidates

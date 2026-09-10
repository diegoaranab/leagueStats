# Architecture

LeagueStats serves Solo Queue and Flex / Clash recommendations through static
JSON and an Angular SPA, without an always-on backend.

## Solo pipeline

```text
LoLalytics -> Python scraper -> exact rank/window/lane matrix
          -> Difficulty scoring -> static Solo JSON
```

The matrix covers NA / LAN / LAS, exact Iron through Master ranks, `current` /
`7d` / `14d`, and top / jungle / middle / bottom / support. Playwright loads the
ladder pages and BeautifulSoup parses champion rows. Lane retries, diagnostics,
partial-data metadata, and last-success backups support resilient generation.
The scraper applies its pick-rate and tier filters and computes champion ranks
and mastery-gap observations before assigning difficulty.

LoLalytics window mapping is deliberate: `current` sends no explicit `patch`
query parameter, `7d` sends `patch=7`, and `14d` sends `patch=14`.
Solo Recommended Bans use champions with positive PBI from the selected lane.

## Difficulty v2

```text
Raw mastery-gap observation -> daily persisted history
                            -> median/MAD winsorization
                            -> recency weighting (seven-day half-life)
                            -> lane/context-relative difficulty classification
```

Daily observations live in `difficulty-history.json` on the dedicated
`difficulty-history` branch. Scoring combines available history with the current
observation; smoothing starts at seven distinct daily samples and uses up to
30 days of history. Without sufficient samples, scoring uses the current
mastery gap. Easy / Medium / Hard classifications compare champions within the
same region, exact rank, window, and lane.

See [Difficulty v2 History](DIFFICULTY_HISTORY.md) for persistence rules, formulas,
and fallback behavior.

## Teamplay pipeline

```text
Solo dataset + Oracle's Elixir professional data
  -> Teamplay builder -> role-specific pro evidence
  -> Flex / Clash ranking + Teamplay Recommended Ban ranking
  -> static Teamplay JSON
```

The builder blends lane-normalized professional pick and role-adjusted ban
evidence with Solo strength. Its eligible pool requires a professional pick and
at least five combined professional picks and bans. Teamplay v3 pick ranking
asks “What should we pick/value?”; the separate denial ranking asks “What should
we deny?” Ban evidence receives role-specific credit through role pick share.
The stored lane arrays retain pick order, with separate ban scores and ranks.

See [Data Schema](DATA_SCHEMA.md#teamplay-recommended-bans) for the scoring
formulas, eligibility, tie breakers, and frontend Recommended Bans behavior.

## Frontend and static data

The Angular SPA reads these paths relative to the deployed app's base URL:

- Solo: `/data/{region}/{tier}/{window}.json`
- Teamplay: `/data/teamplay/{region}/{tier}/{window}.json`
- Manifest: `/data/manifest.json`

Generated files live under `apps/web/public/data/` and are intentionally
gitignored. The results route uses query state for `mode`, `region`, `tier`,
`window`, `lane`, and `sort`. Mode chooses the dataset family; lane and sorting
operate on the loaded data. The responsive lane selector supports mobile use.
Recommended Bans show up to three champions from the selected pool, independently
of Difficulty and Sort.

## CI and deployment

[PR Validation](../.github/workflows/pr-validation.yml) runs on pull requests
targeting `main` and supports manual dispatch. It runs Python offline unit tests,
Python compile validation, and an Angular production build. It performs no
scraping, deployment, or history writes. A newer run cancels an older run for
the same PR/ref.

[Production deployment](../.github/workflows/deploy-pages.yml) runs on pushes to
`main`, manual dispatch, and daily schedules at **00:23 UTC** and **12:23 UTC**.
Both scheduled runs generate fresh Solo and Teamplay datasets for the full
configured matrix, including `current`, `7d`, and `14d`, then build and deploy
the SPA to GitHub Pages. Production runs share the `pages` concurrency group
with cancellation of in-progress runs disabled.

Generation loads existing Difficulty history for scoring. Only the **00:23 UTC
scheduled run** persists daily observations on `difficulty-history`, using a
complete Solo matrix artifact. Push, manual, and 12:23 UTC runs do not write
history. See [Difficulty v2 History](DIFFICULTY_HISTORY.md) for details.

## Oracle source resilience

CI resolves Oracle's Elixir data through a layered strategy:

```text
Fresh download -> alternate download mechanisms -> recent Actions cache
               -> historical Git bootstrap fallback
```

Fresh download attempts use the direct Google Drive URL, an alternate download
endpoint, and gdown. If all fail, a valid cached download no older than seven
days can be used, followed by a known historical CSV from Git as the final
fallback. Only fresh downloads refresh the cache. If no valid source can be
obtained, generation fails.

Degraded sources are identified through dataset `meta.oracle_source` and
`meta.warnings`, so cached or historical professional evidence is distinguishable
from fresh evidence.

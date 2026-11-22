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

- Solo: `data/{region}/{tier}/{window}.json`
- Teamplay: `data/teamplay/{region}/{tier}/{window}.json`
- Manifest: `data/manifest.json`

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
Both scheduled runs and every manual dispatch generate fresh Solo and Teamplay
datasets for the full configured matrix, including `current`, `7d`, and `14d`,
then build and deploy the SPA to GitHub Pages. A normal `main` push instead
restores the last fully validated dataset from the dedicated `production-data`
branch before building. Changes to the scraper or frontend dataset model/loader
conservatively force a fresh generation; deployment-workflow and validator-only
changes do not inherently change recommendation data.

`production-data` is an operational state branch containing only the deployable
dataset under `data/`; generated data remains gitignored on `main`. Fresh output
is validated before that branch is updated, and the build waits for persistence
to succeed. A warning-level `partial` dataset remains deployable when every
expected file and lane is present, champion counts are positive, and
`failed_lanes` is empty. An `error` status, any failed lane, or structural
incompleteness is never deployable.

If `production-data` is missing or invalid during a non-data-sensitive `main`
push, the workflow first downloads the expected matrix from the currently
deployed Pages URL, validates it, and persists it to seed or repair the snapshot
branch. Only an unavailable or invalid Pages recovery falls back to fresh
generation. Pages bootstrap and ordinary snapshot reuse do not create Difficulty
history observations. To request fresh production statistics at any time,
manually run **Deploy Web to GitHub Pages**; manual runs refresh by default. All
production runs share the `pages` concurrency group with cancellation of
in-progress runs disabled.

Generation loads existing Difficulty history for scoring. Only the **00:23 UTC
scheduled run** persists daily observations on `difficulty-history`, using a
complete Solo matrix artifact. Push, manual, and 12:23 UTC runs do not write
history. Unlike `production-data`, which is the last-known-good deployable
snapshot, `difficulty-history` stores the rolling observations used by Difficulty
scoring. See [Difficulty v2 History](DIFFICULTY_HISTORY.md) for details.

## Oracle source resilience

Production retrieves the official Oracle's Elixir CSV through the authenticated
Google Drive API. If that fails, it uses a structurally validated, checksum-verified
cache whose original download is at most 48 hours old; otherwise it fails before
Teamplay generation. Only a validated live download refreshes the cache and its
`downloaded_at`. Cache reuse never renews that timestamp.

`oracle_downloaded_at` determines cache eligibility. `oracle_last_match_at`
records the newest professional match and is observational: an authenticated,
valid download remains current even if the latest match is older than 24 hours.
Cached sources are identified through dataset `meta.oracle_source` and warnings.

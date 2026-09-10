# Roadmap

## Currently implemented

- Angular static-first frontend with onboarding, results, and URL context state
- Exact Iron through Master rank contexts
- NA / LAN / LAS regions
- `current` / `7d` / `14d` windows
- Five lanes: top, jungle, middle, bottom, support
- Resilient Solo scraping with retries, diagnostics, and last-success backups
- Flex / Clash mode using Oracle's Elixir professional evidence and Solo strength
- Teamplay v3 ranking with role-specific pick and ban evidence
- Solo Recommended Bans based on positive PBI
- Teamplay Recommended Bans with separate denial ranking
- Difficulty v2 daily history and historical smoothing
- Responsive/mobile lane selector
- Scheduled production generation and GitHub Pages deployment at 00:23 and 12:23 UTC
- PR validation CI with offline Python tests, compile validation, and Angular production build

## Near-term technical priorities

- Review dependency/security advisories in a separate maintenance pass
- Continue data-quality monitoring across supported contexts
- Monitor Difficulty-history behavior as more daily samples accumulate
- Monitor Oracle source freshness and fallback resilience
- Improve test coverage where it adds meaningful regression protection

## Future product candidates

These are candidates for evaluation, not commitments:

- Matchup-context panels
- Patch-history comparisons
- More regions
- i18n / ES-EN
- Richer advanced filtering, such as ban-rate thresholds and minimum games

See [Architecture](ARCHITECTURE.md) for current data flows and operational behavior.

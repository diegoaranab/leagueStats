# Difficulty History Foundation

Difficulty history is persistence infrastructure for a future Difficulty v2. It does not affect the
current difficulty calculation, labels, or frontend behavior.

## Storage

The scheduled `23 0 * * *` UTC production run updates `difficulty-history.json` on the dedicated
`difficulty-history` branch. The state file is not stored on `main`. Push deployments, manual
deployments, and the `23 12 * * *` UTC production run do not mutate history.

Schema version 1 stores one observation per UTC date for each
`region|tier|window|lane|champion` series:

```json
{
  "schema_version": 1,
  "retention_days": 30,
  "updated_at_utc": "2026-08-30T00:30:00Z",
  "series": {
    "na|gold|7d|top|Aatrox": [
      {
        "date": "2026-08-30",
        "delta": 5.1,
        "win_rate": 49.8,
        "mastery_gap_pct": 9.2
      }
    ]
  }
}
```

Only complete Solo matrices are eligible. Missing champions remain missing, and champions with a
missing or null `mastery_gap_pct` are skipped rather than represented by a synthetic zero. A rerun
replaces the observation for the same UTC date and series. Each series retains only observations in
the latest 30-day UTC window.

## Planned Difficulty v2 (not active)

The planned calculation will use rolling daily observations, robust median/MAD outlier handling,
exponentially decaying recency weights with an approximately seven-day half-life, and a minimum
history threshold before smoothing. Difficulty labels will then use lane/context-relative tertiles
after smoothing.

Median/MAD should reduce sensitivity to anomalous scrapes. Exponential weighting lets recent
observations matter more while retaining useful older evidence without allowing it to dominate.

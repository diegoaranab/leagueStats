# Difficulty v2 History

Difficulty v2 uses persisted daily Solo observations to stabilize champion difficulty without
changing the underlying `mastery_gap_pct` calculation or the Easy/Medium/Hard presentation.

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

## Difficulty v2 scoring

Each scrape selects the exact `region|tier|window|lane|champion` series and combines it with the
current UTC day's `mastery_gap_pct`. Only observations from the last 30 days are eligible. Missing
days stay missing: they are not interpolated or replaced with zero. Future observations are ignored.
If history already includes the current UTC date, the current scrape replaces that value in memory
for scoring. This makes the latest scrape authoritative without modifying the persisted file; only
the midnight persistence job writes history.

Smoothing begins when the effective series contains at least seven distinct daily observations,
including the current scrape. Until then, `difficulty_score` is the current `mastery_gap_pct`, so
bootstrap behavior matches the snapshot-based calculation.

For an eligible series, Difficulty v2 computes the median and median absolute deviation (MAD) of
`mastery_gap_pct`. When MAD is greater than zero, every value is winsorized to:

```text
robust_sigma = 1.4826 * MAD
lower = max(0, median - 3 * robust_sigma)
upper = median + 3 * robust_sigma
```

Outliers are clamped, not deleted. When MAD is zero, values are deliberately left unchanged.

The clamped values are averaged with actual UTC date ages and a seven-day half-life:

```text
weight = 2 ** (-age_days / 7)
difficulty_score = sum(clamped_value * weight) / sum(weight)
```

A value from seven days ago therefore has half today's weight; one from 14 days ago has one quarter.
More history generally improves stability, while exponential decay keeps older observations from
dominating recent evidence.

Finally, champions are sorted by `difficulty_score` only against champions in the same region,
tier, window, and lane. Existing deterministic rank/name tie breakers and approximately equal
tertile boundaries assign Easy, Medium, and Hard labels. Diagnostic sample counts and whether
smoothing was applied are included in generated data, but history details and intermediate MAD
values are not shown in the UI.

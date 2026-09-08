# Data Schema

## Dataset File

Path format:

```text
apps/web/public/data/{region}/{tier}/{window}.json
```

Top-level shape:

```json
{
  "meta": { "...": "..." },
  "data": {
    "top": ["champion", "..."],
    "jungle": [],
    "middle": [],
    "bottom": [],
    "support": []
  }
}
```

## `meta`

- `source`: string
- `region`: `na | lan | las`
- `tier`: `iron | bronze | silver | gold | platinum | emerald | diamond | master`
- `window`: `current | 7d | 14d`
- `min_pick_rate`: number
- `allowed_tiers`: string[]
- `generated_at_utc`: ISO timestamp
- `is_partial`: boolean
- `failed_lanes`: string[]
- `warnings`: string[]
- `difficulty_method`: string
- `difficulty_history_retention_days`: number
- `difficulty_history_min_samples`: number
- `difficulty_history_half_life_days`: number
- `difficulty_history_outlier_method`: string
- `difficulty_history_smoothed_count`: number
- `difficulty_history_fallback_count`: number
- `rank_mode`: string
- `difficulty_colors`: object
- `leagues_used`: string[]
- `patches_used`: string[]
- `total_games_filtered`: number
- `inclusion_mode`: string
- `excluded_zero_pro_count`: number
- `excluded_low_evidence_count`: number
- `score_formula`: string
- `pro_score_formula`: string
- `teamplay_ban_score_method`: string (Teamplay: `teamplay_deny_v1`)
- `teamplay_ban_score_formula`: string (see below)
- `ban_credit_mode`: string
- `eligibility_rule`: string

## Champion Object

- `lane`: lane key
- `rank`: number | null
- `filtered_rank`: number
- `name`: string
- `icon_url`: string | null
- `champion_url`: string | null
- `tier`: string
- `win_rate`: number | null
- `win_delta`: number | null
- `pick_rate`: number | null
- `ban_rate`: number | null
- `pbi`: number | null
- `delta`: number | null
- `best_win_est`: number | null
- `mastery_gap_raw`: number | null
- `mastery_gap_pct`: number | null
- `difficulty_score`: number | null
- `difficulty_history_samples`: number
- `difficulty_history_applied`: boolean
- `difficulty`: `easy | medium | hard | null`
- `difficulty_color`: hex string | null
- `difficulty_order`: number | null
- `teamplay_rank`: number | null
- `teamplay_ban_score`: number | null (Teamplay internal denial score, rounded to 4 decimals)
- `teamplay_ban_rank`: number | null (Teamplay lane ban priority, starting at 1)
- `solo_strength_score`: number | null
- `pro_pick_count`: number
- `pro_role_pick_rate`: number | null
- `pro_ban_count`: number
- `pro_ban_rate`: number | null
- `champion_total_role_picks`: number
- `role_pick_share`: number | null
- `role_adjusted_ban_rate`: number | null
- `pro_win_rate`: number | null
- `pro_score`: number | null
- `flex_clash_score`: number | null
- `pro_flex_roles`: number
- `badges`: string[]

## Manifest File

Path:

```text
apps/web/public/data/manifest.json
```

Contains:

- supported dimensions (`regions`, `tiers`, `windows`, `lanes`)
- top-level manifest `meta.generated_at_utc`
- dataset entries with:
  - `path`
  - `region`
  - `tier`
  - `window`
  - `generated_at_utc`
  - `status`
  - `is_partial`
  - `failed_lanes`
  - `warnings`
  - `champion_count`

## Teamplay Recommended Bans

Teamplay datasets under `data/teamplay/{region}/{tier}/{window}.json` use
`teamplay_ban_score_method: "teamplay_deny_v1"` and this exact
`teamplay_ban_score_formula`:

```text
0.70*normalized_role_adjusted_ban_rate + 0.20*normalized_role_pick_rate + 0.10*solo_strength_score
```

The builder uses its existing lane-normalized professional inputs and Solo strength.
Ban evidence receives role-specific credit through the existing role pick share.
Only the existing eligible Teamplay pool participates; zero pro bans do not exclude
an otherwise eligible champion.

Ban ranks cover the full eligible lane, ordered by rounded ban score descending,
role-adjusted ban rate descending, pro role pick rate descending, Solo strength
descending, Teamplay pick rank ascending, then champion name ascending.
The stored lane array and `teamplay_rank` retain their existing pick order.
The pick formulas remain `0.75*normalized_role_pick_rate + 0.25*normalized_role_adjusted_ban_rate`
for `pro_score` and `0.90*pro_score + 0.10*solo_strength_score` for `flex_clash_score`.

Results show the first three ban ranks (or fewer for smaller pools), independent of
Difficulty and Sort. Lane, mode, region, tier, and window select the source pool.
Teamplay Ban priority sorting and More details use the generated rank; the raw
score is internal. Older datasets without ban ranks show no recommendations until
rebuilt, and missing ranks sort last. Solo retains its positive-PBI recommendations
and existing comparator; Teamplay denial scoring, eligibility, and tie breakers
never read PBI.

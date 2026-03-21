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
- `tier`: `gold_plus | platinum_plus | emerald_plus | diamond_plus | d2_plus | master_plus`
- `window`: `current | 7d | 14d`
- `min_pick_rate`: number
- `allowed_tiers`: string[]
- `generated_at_utc`: ISO timestamp
- `is_partial`: boolean
- `failed_lanes`: string[]
- `warnings`: string[]
- `difficulty_method`: string
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
- `difficulty`: `easy | medium | hard | null`
- `difficulty_color`: hex string | null
- `difficulty_order`: number | null
- `teamplay_rank`: number | null
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

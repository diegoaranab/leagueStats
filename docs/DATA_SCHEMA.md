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

export const REGION_OPTIONS = ['na', 'lan', 'las'] as const;
export const TIER_OPTIONS = [
  'gold_plus',
  'platinum_plus',
  'emerald_plus',
  'diamond_plus',
  'd2_plus',
  'master_plus',
] as const;
export const WINDOW_OPTIONS = ['current', '7d', '14d'] as const;
export const LANE_OPTIONS = ['top', 'jungle', 'middle', 'bottom', 'support'] as const;

export type Region = (typeof REGION_OPTIONS)[number];
export type Tier = (typeof TIER_OPTIONS)[number];
export type WindowKey = (typeof WINDOW_OPTIONS)[number];
export type Lane = (typeof LANE_OPTIONS)[number];

export type SortOption = 'tier' | 'win_rate' | 'pick_rate' | 'difficulty';
export type DifficultyTag = 'easy' | 'medium' | 'hard' | null;
export type DifficultyFilter = DifficultyTag | 'all';

export interface TierlistMeta {
  source: string;
  region: Region;
  tier: Tier;
  window: WindowKey;
  min_pick_rate: number;
  allowed_tiers: string[];
  generated_at_utc: string;
  difficulty_method?: string;
  rank_mode?: string;
  difficulty_colors?: Record<string, string>;
}

export interface Champion {
  lane: Lane;
  rank: number | null;
  filtered_rank?: number;
  name: string;
  icon_url: string | null;
  champion_url: string | null;
  tier: string;
  win_rate: number | null;
  win_delta: number | null;
  pick_rate: number | null;
  ban_rate: number | null;
  pbi: number | null;
  delta: number | null;
  best_win_est?: number | null;
  mastery_gap_raw?: number | null;
  mastery_gap_pct?: number | null;
  difficulty?: DifficultyTag;
  difficulty_color?: string | null;
  difficulty_order?: number | null;
}

export interface TierlistDataset {
  meta: TierlistMeta;
  data: Partial<Record<Lane, Champion[]>>;
}

export interface DataManifest {
  meta: {
    source: string;
    generated_at_utc: string;
  };
  supported: {
    regions: Region[];
    tiers: Tier[];
    windows: WindowKey[];
    lanes: Lane[];
  };
  datasets: Array<{
    region: Region;
    tier: Tier;
    window: WindowKey;
    path: string;
    status: string;
    champion_count?: number;
  }>;
}

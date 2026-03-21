export const REGION_OPTIONS = ['na', 'lan', 'las'] as const;
export const TIER_OPTIONS = [
  'bronze',
  'silver',
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
  is_partial: boolean;
  failed_lanes: Lane[];
  warnings: string[];
  difficulty_method?: string;
  rank_mode?: string;
  difficulty_colors?: Record<string, string>;
  leagues_used?: string[];
  patches_used?: string[];
  total_games_filtered?: number;
  inclusion_mode?: string;
  excluded_zero_pro_count?: number;
  excluded_low_evidence_count?: number;
  score_formula?: string;
  pro_score_formula?: string;
  ban_credit_mode?: string;
  eligibility_rule?: string;
}

export interface Champion {
  lane: Lane;
  rank: number | null;
  filtered_rank?: number;
  teamplay_rank?: number;
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
  solo_strength_score?: number | null;
  pro_pick_count?: number;
  pro_role_pick_rate?: number | null;
  pro_ban_count?: number;
  pro_ban_rate?: number | null;
  champion_total_role_picks?: number;
  role_pick_share?: number | null;
  role_adjusted_ban_rate?: number | null;
  pro_win_rate?: number | null;
  pro_score?: number | null;
  flex_clash_score?: number | null;
  pro_flex_roles?: number;
  badges?: string[];
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
    generated_at_utc: string | null;
    is_partial: boolean;
    failed_lanes: Lane[];
    warnings: string[];
    champion_count: number;
    error?: string;
  }>;
}

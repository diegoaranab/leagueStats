import { Lane, Region, SortOption, Tier, WindowKey } from './tierlist.model';

export const PRODUCT_MODE_OPTIONS = ['solo', 'teamplay'] as const;

export type ProductMode = (typeof PRODUCT_MODE_OPTIONS)[number];

export interface ResultsQuery {
  mode: ProductMode;
  region: Region;
  tier: Tier;
  window: WindowKey;
  lane: Lane;
  sort: SortOption;
}

export interface ModeDetail {
  label: string;
  shortLabel: string;
  kicker: string;
  description: string;
  helper: string;
  summary: string;
}

export const DEFAULT_RESULTS_QUERY: ResultsQuery = {
  mode: 'solo',
  region: 'na',
  tier: 'diamond_plus',
  window: '7d',
  lane: 'top',
  sort: 'tier',
};

export const MODE_DETAILS: Record<ProductMode, ModeDetail> = {
  solo: {
    label: 'Solo Queue',
    shortLabel: 'Solo',
    kicker: 'Ladder Context',
    description: 'Recommendations tuned for your rank, region, and recent ranked data.',
    helper: 'Best when you want reliable ladder picks for everyday ranked games.',
    summary: 'Based on ladder context and recent ranked performance for the exact queue slice you selected.',
  },
  teamplay: {
    label: 'Flex / Clash',
    shortLabel: 'Flex / Clash',
    kicker: 'Coordinated Play',
    description: 'Draft-aware picks that blend pro presence with ladder viability.',
    helper: 'Best when your team wants stronger draft signals without ignoring solo strength.',
    summary: 'Based on pro draft presence, ban pressure, and whether the pick still holds up in ladder play.',
  },
};

export const REGION_LABELS: Record<Region, string> = {
  na: 'North America',
  lan: 'Latin America North',
  las: 'Latin America South',
};

export const REGION_SHORT_LABELS: Record<Region, string> = {
  na: 'NA',
  lan: 'LAN',
  las: 'LAS',
};

export const TIER_LABELS: Record<Tier, string> = {
  bronze: 'Bronze+',
  silver: 'Silver+',
  gold_plus: 'Gold+',
  platinum_plus: 'Platinum+',
  emerald_plus: 'Emerald+',
  diamond_plus: 'Diamond+',
  d2_plus: 'D2+',
  master_plus: 'Master+',
};

export const WINDOW_LABELS: Record<WindowKey, string> = {
  current: 'Current Patch',
  '7d': 'Last 7 Days',
  '14d': 'Last 14 Days',
};

export const LANE_LABELS: Record<Lane, string> = {
  top: 'Top',
  jungle: 'Jungle',
  middle: 'Mid',
  bottom: 'ADC',
  support: 'Support',
};

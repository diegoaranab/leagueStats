import { ParamMap } from '@angular/router';
import { DEFAULT_RESULTS_QUERY, PRODUCT_MODE_OPTIONS, ResultsQuery } from './selection.model';
import { DifficultyFilter, LANE_OPTIONS, normalizeTier, REGION_OPTIONS, SortOption, WINDOW_OPTIONS } from './tierlist.model';

function read<T extends string>(value: string | null, allowed: readonly T[], fallback: T): T {
  return value && (allowed as readonly string[]).includes(value) ? value as T : fallback;
}

export function readResultsQuery(params: ParamMap): ResultsQuery {
  const defaults = DEFAULT_RESULTS_QUERY;
  return {
    mode: read(params.get('mode'), PRODUCT_MODE_OPTIONS, defaults.mode),
    region: read(params.get('region'), REGION_OPTIONS, defaults.region),
    tier: normalizeTier(params.get('tier'), defaults.tier),
    window: read(params.get('window'), WINDOW_OPTIONS, defaults.window),
    lane: read(params.get('lane'), LANE_OPTIONS, defaults.lane),
    sort: read<SortOption>(params.get('sort'), ['tier', 'win_rate', 'pick_rate', 'difficulty', 'ban_priority'], defaults.sort),
    difficulty: read<Exclude<DifficultyFilter, null>>(params.get('difficulty'), ['all', 'easy', 'medium', 'hard'], defaults.difficulty),
  };
}

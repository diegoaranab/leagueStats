import {
  Champion,
  LANE_OPTIONS,
  Lane,
  TierlistDataset,
} from '../models/tierlist.model';

export const EASY_CLASH_LANES: readonly Lane[] = LANE_OPTIONS;

export interface EasyClashLineupSlot {
  lane: Lane;
  champion: Champion;
  teamplayRank: number;
}

export interface EasyClashLineupAvailable {
  available: true;
  slots: EasyClashLineupSlot[];
}

export interface EasyClashLineupUnavailable {
  available: false;
  reason: 'missing-role' | 'not-enough-unique-champions' | 'no-unique-assignment';
  missingLanes: Lane[];
  uniqueCandidateCount: number;
}

export type EasyClashLineupResult =
  | EasyClashLineupAvailable
  | EasyClashLineupUnavailable;

interface Candidate {
  champion: Champion;
  rank: number;
}

interface BestAssignment {
  totalRank: number;
  slots: EasyClashLineupSlot[];
}

/**
 * Finds the globally strongest Easy-only Teamplay assignment across all five
 * roles. Difficulty is eligibility-only; canonical Teamplay rank is the sole
 * optimization input.
 */
export function buildEasyClashLineup(dataset: TierlistDataset): EasyClashLineupResult {
  const candidatesByLane = new Map<
    Lane,
    Candidate[]
  >(
    EASY_CLASH_LANES.map((lane) => [lane, buildCandidates(dataset, lane)]),
  );
  const missingLanes = EASY_CLASH_LANES.filter(
    (lane) => candidatesByLane.get(lane)?.length === 0,
  );
  const uniqueCandidateCount = new Set(
    EASY_CLASH_LANES.flatMap(
      (lane) => (candidatesByLane.get(lane) ?? []).map(({ champion }) => champion.name),
    ),
  ).size;

  if (missingLanes.length) {
    return {
      available: false,
      reason: 'missing-role',
      missingLanes,
      uniqueCandidateCount,
    };
  }

  if (uniqueCandidateCount < EASY_CLASH_LANES.length) {
    return {
      available: false,
      reason: 'not-enough-unique-champions',
      missingLanes: [],
      uniqueCandidateCount,
    };
  }

  // Exploring the most constrained roles first reduces search work without
  // affecting the fixed role order used for output and deterministic ties.
  const searchLanes = [...EASY_CLASH_LANES].sort((a, b) =>
    (candidatesByLane.get(a)?.length ?? 0) - (candidatesByLane.get(b)?.length ?? 0)
    || EASY_CLASH_LANES.indexOf(a) - EASY_CLASH_LANES.indexOf(b),
  );
  const minimumRemainingRanks = Array(searchLanes.length + 1).fill(0) as number[];

  for (let index = searchLanes.length - 1; index >= 0; index -= 1) {
    minimumRemainingRanks[index] = minimumRemainingRanks[index + 1]
      + candidatesByLane.get(searchLanes[index])![0].rank;
  }

  const selectedByLane = new Map<Lane, Candidate>();
  const usedChampionNames = new Set<string>();
  const best: { value: BestAssignment | null } = { value: null };

  const search = (searchIndex: number, currentTotal: number): void => {
    if (best.value && currentTotal + minimumRemainingRanks[searchIndex] > best.value.totalRank) {
      return;
    }

    if (searchIndex === searchLanes.length) {
      const slots = EASY_CLASH_LANES.map((lane) => {
        const selected = selectedByLane.get(lane)!;
        return {
          lane,
          champion: selected.champion,
          teamplayRank: selected.rank,
        };
      });
      const assignment = { totalRank: currentTotal, slots };

      if (!best.value || compareAssignments(assignment, best.value) < 0) {
        best.value = assignment;
      }
      return;
    }

    const lane = searchLanes[searchIndex];

    for (const candidate of candidatesByLane.get(lane)!) {
      if (usedChampionNames.has(candidate.champion.name)) {
        continue;
      }

      const nextTotal = currentTotal + candidate.rank;
      if (best.value && nextTotal + minimumRemainingRanks[searchIndex + 1] > best.value.totalRank) {
        break;
      }

      selectedByLane.set(lane, candidate);
      usedChampionNames.add(candidate.champion.name);
      search(searchIndex + 1, nextTotal);
      usedChampionNames.delete(candidate.champion.name);
      selectedByLane.delete(lane);
    }
  };

  search(0, 0);

  if (!best.value) {
    return {
      available: false,
      reason: 'no-unique-assignment',
      missingLanes: [],
      uniqueCandidateCount,
    };
  }

  return { available: true, slots: best.value.slots };
}

function buildCandidates(dataset: TierlistDataset, lane: Lane): Candidate[] {
  const bestByName = new Map<string, Candidate>();

  for (const champion of dataset.data[lane] ?? []) {
    if (champion.difficulty !== 'easy') {
      continue;
    }

    const rank = canonicalTeamplayRank(champion);
    if (rank === null) {
      continue;
    }

    const current = bestByName.get(champion.name);
    if (!current || rank < current.rank) {
      bestByName.set(champion.name, { champion, rank });
    }
  }

  return [...bestByName.values()].sort((a, b) =>
    a.rank - b.rank || compareNames(a.champion.name, b.champion.name),
  );
}

function canonicalTeamplayRank(champion: Champion): number | null {
  const rank = champion.teamplay_rank ?? champion.filtered_rank ?? champion.rank;
  return typeof rank === 'number' && Number.isFinite(rank) && rank > 0 ? rank : null;
}

function compareAssignments(a: BestAssignment, b: BestAssignment): number {
  if (a.totalRank !== b.totalRank) {
    return a.totalRank - b.totalRank;
  }

  for (let index = 0; index < EASY_CLASH_LANES.length; index += 1) {
    const rankDifference = a.slots[index].teamplayRank - b.slots[index].teamplayRank;
    if (rankDifference !== 0) {
      return rankDifference;
    }
  }

  for (let index = 0; index < EASY_CLASH_LANES.length; index += 1) {
    const nameDifference = compareNames(
      a.slots[index].champion.name,
      b.slots[index].champion.name,
    );
    if (nameDifference !== 0) {
      return nameDifference;
    }
  }

  return 0;
}

function compareNames(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

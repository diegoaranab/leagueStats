import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSidenavModule } from '@angular/material/sidenav';
import { map } from 'rxjs';

import { ChampionCardComponent } from '../../components/champion-card/champion-card.component';
import { FilterBarComponent } from '../../components/filter-bar/filter-bar.component';
import { InfoTooltipComponent } from '../../components/info-tooltip/info-tooltip.component';
import { LaneTabsComponent } from '../../components/lane-tabs/lane-tabs.component';
import {
  DEFAULT_RESULTS_QUERY,
  LANE_LABELS,
  MODE_DETAILS,
  PRODUCT_MODE_OPTIONS,
  ProductMode,
  REGION_SHORT_LABELS,
  ResultsQuery,
  TIER_LABELS,
  WINDOW_LABELS,
} from '../../core/models/selection.model';
import {
  Champion,
  DifficultyFilter,
  LANE_OPTIONS,
  Lane,
  REGION_OPTIONS,
  Region,
  SortOption,
  TIER_OPTIONS,
  Tier,
  TierlistDataset,
  WINDOW_OPTIONS,
  WindowKey,
} from '../../core/models/tierlist.model';
import { TierlistService } from '../../core/services/tierlist.service';

@Component({
  selector: 'app-results-page',
  imports: [
    CommonModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSidenavModule,
    LaneTabsComponent,
    FilterBarComponent,
    ChampionCardComponent,
    InfoTooltipComponent,
  ],
  templateUrl: './results-page.component.html',
  styleUrl: './results-page.component.css',
})
export class ResultsPageComponent implements OnInit {
  readonly laneOrder: Lane[] = [...LANE_OPTIONS];
  readonly laneLabels = LANE_LABELS;
  readonly modeDetails = MODE_DETAILS;
  readonly regionShortLabels = REGION_SHORT_LABELS;
  readonly tierLabels = TIER_LABELS;
  readonly windowLabels = WINDOW_LABELS;

  private readonly destroyRef = inject(DestroyRef);
  private readonly breakpointObserver = inject(BreakpointObserver);

  readonly isCompact = toSignal(
    this.breakpointObserver.observe('(max-width: 1080px)').pipe(map((state) => state.matches)),
    { initialValue: false },
  );

  isLoading = true;
  errorMessage = '';
  filtersOpen = false;
  availableLanes: Lane[] = [...LANE_OPTIONS];
  laneCounts: Partial<Record<Lane, number>> = {};
  champions: Champion[] = [];
  difficultyFilter: DifficultyFilter = 'all';

  query: ResultsQuery = { ...DEFAULT_RESULTS_QUERY };

  private dataset: TierlistDataset | null = null;
  private datasetKey = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly tierlistService: TierlistService,
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const mode = this.readParam(params.get('mode'), PRODUCT_MODE_OPTIONS, DEFAULT_RESULTS_QUERY.mode);
        const region = this.readParam(params.get('region'), REGION_OPTIONS, DEFAULT_RESULTS_QUERY.region);
        const tier = this.readParam(params.get('tier'), TIER_OPTIONS, DEFAULT_RESULTS_QUERY.tier);
        const window = this.readParam(params.get('window'), WINDOW_OPTIONS, DEFAULT_RESULTS_QUERY.window);
        const lane = this.readParam(params.get('lane'), LANE_OPTIONS, DEFAULT_RESULTS_QUERY.lane);
        const sort = this.readParam<SortOption>(
          params.get('sort'),
          ['tier', 'win_rate', 'pick_rate', 'difficulty'] as const,
          DEFAULT_RESULTS_QUERY.sort,
        );

        this.query = { mode, region, tier, window, lane, sort };

        const nextKey = `${mode}:${region}:${tier}:${window}`;
        if (nextKey !== this.datasetKey) {
          this.loadDataset(nextKey);
          return;
        }

        this.refreshView();
      });
  }

  onLaneChange(lane: Lane): void {
    this.updateQuery({ lane });
  }

  onSortChange(sort: SortOption): void {
    this.updateQuery({ sort });
  }

  onDifficultyChange(filter: DifficultyFilter): void {
    this.difficultyFilter = filter;
    this.refreshView();
  }

  onModeChange(mode: ProductMode): void {
    this.updateQuery({ mode, sort: DEFAULT_RESULTS_QUERY.sort });
  }

  onRegionChange(region: Region): void {
    this.updateQuery({ region });
  }

  onTierChange(tier: Tier): void {
    this.updateQuery({ tier });
  }

  onWindowChange(window: WindowKey): void {
    this.updateQuery({ window });
  }

  openFilters(): void {
    this.filtersOpen = true;
  }

  closeFilters(): void {
    this.filtersOpen = false;
  }

  trackByChampion(_index: number, champion: Champion): string {
    return champion.name;
  }

  get currentMode() {
    return this.modeDetails[this.query.mode];
  }

  get datasetMeta() {
    return this.dataset?.meta ?? null;
  }

  get laneHeadline(): string {
    return `${this.laneLabels[this.query.lane]} picks`;
  }

  get hasDatasetWarning(): boolean {
    return Boolean(
      this.datasetMeta && (this.datasetMeta.is_partial || this.datasetMeta.warnings.length || this.datasetMeta.failed_lanes.length),
    );
  }

  get warningMessage(): string {
    if (!this.datasetMeta) {
      return '';
    }

    const failedLanes = this.datasetMeta.failed_lanes.map((lane) => this.laneLabels[lane]);
    const failedCopy = failedLanes.length ? `Unavailable lanes: ${failedLanes.join(', ')}.` : '';
    const warningCopy = this.datasetMeta.warnings[0] ?? 'Some of the underlying data is partial.';

    return `${warningCopy} ${failedCopy}`.trim();
  }

  private loadDataset(nextKey: string): void {
    this.datasetKey = nextKey;
    this.dataset = null;
    this.champions = [];
    this.laneCounts = {};
    this.errorMessage = '';
    this.isLoading = true;

    const requestKey = nextKey;
    const dataset$ = this.query.mode === 'teamplay'
      ? this.tierlistService.getTeamplayDataset(this.query.region, this.query.tier, this.query.window)
      : this.tierlistService.getDataset(this.query.region, this.query.tier, this.query.window);

    dataset$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (dataset) => {
          if (this.datasetKey !== requestKey) {
            return;
          }

          this.dataset = dataset;
          this.filtersOpen = false;
          this.availableLanes = this.laneOrder.filter((lane) => Array.isArray(dataset.data[lane]));
          this.laneCounts = this.laneOrder.reduce<Partial<Record<Lane, number>>>((counts, lane) => {
            counts[lane] = dataset.data[lane]?.length ?? 0;
            return counts;
          }, {});
          if (!this.availableLanes.length) {
            this.availableLanes = [...this.laneOrder];
          }
          if (!this.availableLanes.includes(this.query.lane)) {
            this.updateQuery({ lane: this.availableLanes[0] });
            return;
          }
          this.isLoading = false;
          this.refreshView();
        },
        error: () => {
          if (this.datasetKey !== requestKey) {
            return;
          }

          this.errorMessage =
            this.query.mode === 'teamplay'
              ? 'No teamplay dataset is available for this selection yet.'
              : 'No solo queue dataset is available for this selection yet.';
          this.isLoading = false;
        },
      });
  }

  private refreshView(): void {
    if (!this.dataset) {
      return;
    }

    const laneChampions = this.dataset.data[this.query.lane] ?? [];
    let next = [...laneChampions];

    if (this.difficultyFilter !== 'all') {
      next = next.filter((champion) => champion.difficulty === this.difficultyFilter);
    }

    switch (this.query.sort) {
      case 'win_rate':
        next.sort((a, b) => (b.win_rate ?? -1) - (a.win_rate ?? -1));
        break;
      case 'pick_rate':
        next.sort((a, b) => (b.pick_rate ?? -1) - (a.pick_rate ?? -1));
        break;
      case 'difficulty':
        next.sort((a, b) => (a.difficulty_order ?? 999) - (b.difficulty_order ?? 999));
        break;
      default:
        next.sort((a, b) => {
          const rankA = this.query.mode === 'teamplay'
            ? a.teamplay_rank ?? a.filtered_rank ?? a.rank ?? 999
            : a.filtered_rank ?? a.rank ?? 999;
          const rankB = this.query.mode === 'teamplay'
            ? b.teamplay_rank ?? b.filtered_rank ?? b.rank ?? 999
            : b.filtered_rank ?? b.rank ?? 999;

          return rankA - rankB;
        });
        break;
    }

    this.champions = next;
  }

  private updateQuery(update: Partial<ResultsQuery>): void {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: update,
      queryParamsHandling: 'merge',
    });
  }

  private readParam<T extends string>(
    value: string | null,
    allowed: readonly T[],
    fallback: T,
  ): T {
    if (value && (allowed as readonly string[]).includes(value)) {
      return value as T;
    }
    return fallback;
  }
}





import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule, ViewportScroller } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, ChangeDetectionStrategy, afterNextRender, ElementRef, Injector } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationStart, Router, RouterLink, Scroll } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSidenavModule } from '@angular/material/sidenav';
import { map, Subscription } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { ChampionCardComponent } from '../../components/champion-card/champion-card.component';
import { EasyClashLineupComponent } from '../../components/easy-clash-lineup/easy-clash-lineup.component';
import { FilterBarComponent } from '../../components/filter-bar/filter-bar.component';
import { LaneTabsComponent } from '../../components/lane-tabs/lane-tabs.component';
import { RecommendedBansComponent } from '../../components/recommended-bans/recommended-bans.component';
import {
  DEFAULT_RESULTS_QUERY,
  LANE_LABELS,
  MODE_DETAILS,
  ProductMode,
  REGION_LABELS,
  ResultsQuery,
  TIER_LABELS,
  WINDOW_LABELS,
} from '../../core/models/selection.model';
import {
  Champion,
  DifficultyFilter,
  LANE_OPTIONS,
  Lane,
  LEGACY_TIER_ALIASES,
  Region,
  SortOption,
  Tier,
  TierlistDataset,
  WindowKey,
} from '../../core/models/tierlist.model';
import { readResultsQuery } from '../../core/models/results-query';
import { TierlistService } from '../../core/services/tierlist.service';
import {
  buildEasyClashLineup,
  EasyClashLineupResult,
} from '../../core/utils/easy-clash-lineup';

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
    EasyClashLineupComponent,
    RecommendedBansComponent,
  ],
  templateUrl: './results-page.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './results-page.component.css',
})
export class ResultsPageComponent implements OnInit {
  readonly laneOrder: Lane[] = [...LANE_OPTIONS];
  readonly laneLabels = LANE_LABELS;
  readonly modeDetails = MODE_DETAILS;
  readonly regionLabels = REGION_LABELS;
  readonly sortLabels: Record<SortOption, string> = { tier: 'Tier rank', win_rate: 'Win rate', pick_rate: 'Pick rate', difficulty: 'Difficulty', ban_priority: 'Ban priority' };
  readonly tierLabels = TIER_LABELS;
  readonly windowLabels = WINDOW_LABELS;

  private readonly destroyRef = inject(DestroyRef);
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly injector = inject(Injector);
  private readonly viewportScroller = inject(ViewportScroller);
  private historyNavigationId: number | null = null;
  private historyPosition: [number, number] | null = null;
  private datasetRendered = false;

  readonly isCompact = toSignal(
    this.breakpointObserver.observe('(max-width: 1080px)').pipe(map((state) => state.matches)),
    { initialValue: false },
  );

  requestState: 'loading' | 'success' | 'unavailable' | 'failure' = 'loading';
  showSpinner = false;
  private request?: Subscription;
  private requestId = 0;
  private retryFocusPending = false;
  private readonly cancelRetryFocus = () => { this.retryFocusPending = false; };
  private spinnerTimer?: ReturnType<typeof setTimeout>;
  get isLoading(): boolean { return this.requestState === 'loading'; }
  filtersOpen = false;
  availableLanes: Lane[] = [...LANE_OPTIONS];
  laneCounts: Partial<Record<Lane, number>> = {};
  champions: Champion[] = [];
  spotlightChampion: Champion | null = null;
  spotlightRank: number | null = null;
  recommendedBans: Champion[] = [];
  easyClashLineup: EasyClashLineupResult | null = null;
  easyClashLineupExpanded = false;
  get difficultyFilter(): DifficultyFilter { return this.query.difficulty; }

  query: ResultsQuery = { ...DEFAULT_RESULTS_QUERY };

  private dataset: TierlistDataset | null = null;
  private datasetKey = '';
  private banPriorities = new Map<string, number>();

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly tierlistService: TierlistService,
    private readonly element: ElementRef<HTMLElement>,
  ) {
    const navigation = this.router.currentNavigation();
    const trigger = navigation?.trigger;
    this.historyNavigationId = trigger === 'popstate' ? navigation!.id : null;
    this.router.events.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.historyNavigationId = event.navigationTrigger === 'popstate' ? event.id : null;
        this.historyPosition = null;
      } else if (event instanceof Scroll && event.routerEvent.id === this.historyNavigationId && event.position) {
        this.historyPosition = event.position;
        this.restoreHistoryPosition();
      }
    });
    afterNextRender(() => {
      if (trigger !== 'popstate') {
        this.element.nativeElement.querySelector<HTMLElement>('h1')?.focus({ preventScroll: true });
      }
    });
  }

  ngOnInit(): void {
    this.destroyRef.onDestroy(() => {
      this.requestId++;
      this.request?.unsubscribe();
      clearTimeout(this.spinnerTimer);
      this.stopRetryFocusTracking();
    });
    this.breakpointObserver.observe('(max-width: 1080px)')
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(({ matches }) => {
        if (!matches && this.filtersOpen) this.closeFilters();
      });

    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const rawTier = params.get('tier');
        this.query = readResultsQuery(params);
        const { mode, region, tier, window } = this.query;

        if (rawTier && Object.hasOwn(LEGACY_TIER_ALIASES, rawTier)) {
          void this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { tier },
            queryParamsHandling: 'merge',
            replaceUrl: true,
            scroll: 'manual',
          });
        }

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
    if (filter !== null) {
      this.updateQuery({ difficulty: filter });
    }
  }

  clearDifficulty(): void {
    this.onDifficultyChange('all');
    afterNextRender(() => this.element.nativeElement.querySelector<HTMLElement>('#picks-heading')?.focus({ preventScroll: true }), { injector: this.injector });
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

  focusFilters(): void {
    const heading = this.element.nativeElement.querySelector<HTMLElement>('.results-shell__drawer h2');
    heading?.scrollIntoView({ block: 'center' });
    heading?.focus({ preventScroll: true });
  }

  restoreFilterFocus(): void {
    if (this.filtersOpen) return;
    const target = this.element.nativeElement.querySelector<HTMLElement>('.filters-trigger')
      ?? this.element.nativeElement.querySelector<HTMLElement>('h1');
    target?.focus();
  }

  trackByChampion(_index: number, champion: Champion): string {
    return champion.name;
  }

  jumpToCanonical(): void {
    this.element.nativeElement.querySelector<HTMLElement>('#canonical-pick')?.scrollIntoView({ block: 'center' });
  }

  jumpToTask(id: string): void {
    const heading = this.element.nativeElement.querySelector<HTMLElement>(`#${id}`);
    heading?.scrollIntoView({ block: 'start' });
    heading?.focus({ preventScroll: true });
  }

  banPriorityFor(champion: Champion): number | null {
    return this.banPriorities.get(champion.name) ?? null;
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

  get warnings(): string[] { return this.datasetMeta?.warnings ?? []; }
  get failedLanes(): Lane[] { return this.datasetMeta?.failed_lanes ?? []; }
  get missingLanes(): Lane[] { return this.dataset ? this.laneOrder.filter(lane => !Array.isArray(this.dataset?.data[lane])) : []; }
  get hasDatasetWarning(): boolean {
    return Boolean(this.datasetMeta?.is_partial || this.failedLanes.length ||
      this.warnings.some((warning) => /only had .* patch|datacompleteness|source dataset is partial/i.test(warning)));
  }
  get qualityMessage(): string {
    const notes: string[] = [];
    if (this.failedLanes.length || this.warnings.some(w => /solo source dataset is partial/i.test(w))) notes.push('Ladder coverage is limited.');
    if (this.warnings.some(w => /only had .* patch|datacompleteness/i.test(w))) notes.push('Professional coverage is limited.');
    if (!notes.length && this.datasetMeta?.is_partial) notes.push('Some underlying data is partial.');
    return notes.join(' ');
  }
  get lineupDataUnavailable(): boolean {
    return this.missingLanes.length > 0 || this.failedLanes.some(lane => !this.dataset?.data[lane]?.length);
  }
  get laneAvailability(): 'eligible' | 'filtered' | 'empty' | 'unavailable' {
    const lane = this.dataset?.data[this.query.lane];
    if (!Array.isArray(lane) || (this.failedLanes.includes(this.query.lane) && !lane.length)) return 'unavailable';
    if (!lane.length) return 'empty';
    return this.champions.length ? 'eligible' : 'filtered';
  }
  get statusText(): string {
    switch (this.requestState) {
      case 'loading': return 'Loading recommendations';
      case 'unavailable': return 'The selected dataset is unavailable. Change setup or filters to choose another context.';
      case 'failure': return 'Recommendations could not be loaded. Try again.';
      case 'success': return this.hasDatasetWarning ? 'Limited data coverage' : this.warnings.length || this.datasetMeta?.is_partial === undefined ? 'Dataset loaded; see data details' : 'Dataset ready';
    }
  }
  retry(event: Event): void {
    const ownedFocus = document.activeElement === event.currentTarget;
    this.loadDataset(this.datasetKey, ownedFocus);
  }

  private loadDataset(nextKey: string, retryFocus = false): void {
    this.request?.unsubscribe();
    this.stopRetryFocusTracking();
    this.retryFocusPending = retryFocus;
    if (retryFocus) {
      document.addEventListener('pointerdown', this.cancelRetryFocus, true);
      document.addEventListener('keydown', this.cancelRetryFocus, true);
      document.addEventListener('focusin', this.cancelRetryFocus, true);
    }
    clearTimeout(this.spinnerTimer);
    const requestId = ++this.requestId;
    this.datasetRendered = false;
    this.datasetKey = nextKey;
    this.dataset = null;
    this.champions = [];
    this.spotlightChampion = null;
    this.spotlightRank = null;
    this.recommendedBans = [];
    this.easyClashLineup = null;
    this.banPriorities.clear();
    this.laneCounts = {};
    this.availableLanes = [...this.laneOrder];
    this.requestState = 'loading';
    this.showSpinner = false;
    this.spinnerTimer = setTimeout(() => { if (requestId === this.requestId) this.showSpinner = true; }, 200);
    const historyNavigationId = this.historyNavigationId;
    const dataset$ = this.query.mode === 'teamplay'
      ? this.tierlistService.getTeamplayDataset(this.query.region, this.query.tier, this.query.window)
      : this.tierlistService.getDataset(this.query.region, this.query.tier, this.query.window);
    this.request = dataset$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dataset) => {
        if (requestId !== this.requestId) return;
        if (!this.isValidDataset(dataset)) {
          this.finishFailure('failure');
          return;
        }
        clearTimeout(this.spinnerTimer);
        this.dataset = dataset;
        this.easyClashLineup = this.query.mode === 'teamplay' ? buildEasyClashLineup(dataset) : null;
        this.availableLanes = this.laneOrder.filter(lane => Array.isArray(dataset.data[lane]) && (dataset.data[lane]!.length > 0 || !this.failedLanes.includes(lane)));
        this.laneCounts = this.laneOrder.reduce<Partial<Record<Lane, number>>>((counts, lane) => {
          if (Array.isArray(dataset.data[lane])) counts[lane] = dataset.data[lane]!.length;
          return counts;
        }, {});
        this.requestState = 'success';
        this.refreshView();
        afterNextRender(() => {
          if (requestId !== this.requestId) return;
          if (this.retryFocusPending && (document.activeElement === document.body || !document.activeElement?.isConnected)) {
            this.element.nativeElement.querySelector<HTMLElement>('#picks-heading')?.focus({ preventScroll: true });
          }
          this.stopRetryFocusTracking();
          if (historyNavigationId !== null && this.historyNavigationId === historyNavigationId) {
            this.datasetRendered = true;
            this.restoreHistoryPosition();
          }
        }, { injector: this.injector });
      },
      error: (error: unknown) => {
        if (requestId !== this.requestId) return;
        this.finishFailure(error instanceof HttpErrorResponse && (error.status === 404 || error.status === 410) ? 'unavailable' : 'failure');
      },
    });
  }

  private isValidDataset(dataset: TierlistDataset): boolean {
    if (!dataset || typeof dataset !== 'object' || !dataset.data || typeof dataset.data !== 'object' || Array.isArray(dataset.data) || !dataset.meta || typeof dataset.meta !== 'object' || Array.isArray(dataset.meta)) return false;
    const meta = dataset.meta;
    if (meta.generated_at_utc && (typeof meta.generated_at_utc !== 'string' || !Number.isFinite(Date.parse(meta.generated_at_utc)))) return false;
    if (meta.warnings != null && (!Array.isArray(meta.warnings) || meta.warnings.some(w => typeof w !== 'string'))) return false;
    if (meta.failed_lanes != null && (!Array.isArray(meta.failed_lanes) || meta.failed_lanes.some(lane => !this.laneOrder.includes(lane)))) return false;
    if (meta.leagues_used != null && !Array.isArray(meta.leagues_used)) return false;
    if (meta.patches_used != null && !Array.isArray(meta.patches_used)) return false;
    return this.laneOrder.every(lane => {
      const champions = dataset.data[lane];
      return champions == null || (Array.isArray(champions) && champions.every(champion => champion && typeof champion === 'object' && typeof champion.name === 'string'));
    });
  }

  private stopRetryFocusTracking(): void {
    document.removeEventListener('pointerdown', this.cancelRetryFocus, true);
    document.removeEventListener('keydown', this.cancelRetryFocus, true);
    document.removeEventListener('focusin', this.cancelRetryFocus, true);
    this.retryFocusPending = false;
  }

  private finishFailure(state: 'unavailable' | 'failure'): void {
    this.stopRetryFocusTracking();
    clearTimeout(this.spinnerTimer);
    this.showSpinner = false;
    this.requestState = state;
    const requestId = this.requestId;
    const historyNavigationId = this.historyNavigationId;
    if (historyNavigationId !== null) {
      afterNextRender(() => {
        if (requestId === this.requestId && historyNavigationId === this.historyNavigationId) {
          this.datasetRendered = true;
          this.restoreHistoryPosition();
        }
      }, { injector: this.injector });
    }
  }

  private refreshView(): void {
    if (!this.dataset) {
      return;
    }

    const laneChampions = this.dataset.data[this.query.lane] ?? [];
    this.selectSpotlight(laneChampions);
    const rankedBans = this.query.mode === 'solo'
      ? laneChampions
          .filter((champion) => champion.pbi !== null && champion.pbi > 0)
          .sort((a, b) => this.compareBanPriority(a, b))
      : laneChampions
          .filter((champion) => (champion.teamplay_ban_rank ?? 0) > 0)
          .sort((a, b) => this.compareBanPriority(a, b));

    this.banPriorities = new Map(
      rankedBans.map((champion, index) => [
        champion.name, this.query.mode === 'teamplay' ? champion.teamplay_ban_rank! : index + 1,
      ]),
    );
    this.recommendedBans = rankedBans.slice(0, 3);

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
      case 'ban_priority':
        next.sort((a, b) => this.compareBanPriority(a, b));
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

  private restoreHistoryPosition(): void {
    if (this.datasetRendered && this.historyPosition) {
      this.viewportScroller.scrollToPosition(this.historyPosition);
      this.historyPosition = null;
      this.historyNavigationId = null;
    }
  }

  private selectSpotlight(laneChampions: Champion[]): void {
    let strongestChampion: Champion | null = null;
    let strongestRank: number | null = null;

    for (const champion of laneChampions) {
      if (this.difficultyFilter !== 'all' && champion.difficulty !== this.difficultyFilter) {
        continue;
      }

      const rank = this.canonicalRankFor(champion);
      if (rank === null) {
        continue;
      }

      if (
        strongestRank === null
        || rank < strongestRank
        || (rank === strongestRank && champion.name.localeCompare(strongestChampion?.name ?? '') < 0)
      ) {
        strongestChampion = champion;
        strongestRank = rank;
      }
    }

    this.spotlightChampion = strongestChampion;
    this.spotlightRank = strongestRank;
  }

  private canonicalRankFor(champion: Champion): number | null {
    const rank = this.query.mode === 'teamplay'
      ? champion.teamplay_rank ?? champion.filtered_rank ?? champion.rank
      : champion.filtered_rank ?? champion.rank;

    return typeof rank === 'number' && Number.isFinite(rank) && rank > 0 ? rank : null;
  }

  private compareBanPriority(a: Champion, b: Champion): number {
    if (this.query.mode === 'teamplay') {
      return (a.teamplay_ban_rank ?? Number.MAX_SAFE_INTEGER)
        - (b.teamplay_ban_rank ?? Number.MAX_SAFE_INTEGER)
        || a.name.localeCompare(b.name);
    }

    const positiveA = a.pbi !== null && a.pbi > 0;
    const positiveB = b.pbi !== null && b.pbi > 0;

    if (positiveA !== positiveB) {
      return positiveA ? -1 : 1;
    }

    if (positiveA && positiveB && a.pbi !== b.pbi) {
      return (b.pbi ?? 0) - (a.pbi ?? 0);
    }

    const rankA = a.filtered_rank ?? a.rank ?? Number.MAX_SAFE_INTEGER;
    const rankB = b.filtered_rank ?? b.rank ?? Number.MAX_SAFE_INTEGER;

    return rankA - rankB || a.name.localeCompare(b.name);
  }

  private updateQuery(update: Partial<ResultsQuery>): void {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: update,
      queryParamsHandling: 'merge',
      scroll: 'manual',
    });
  }

}

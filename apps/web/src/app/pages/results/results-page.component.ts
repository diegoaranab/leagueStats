import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subject, takeUntil } from 'rxjs';

import { ChampionCardComponent } from '../../components/champion-card/champion-card.component';
import { FilterBarComponent } from '../../components/filter-bar/filter-bar.component';
import { InfoTooltipComponent } from '../../components/info-tooltip/info-tooltip.component';
import { LaneTabsComponent } from '../../components/lane-tabs/lane-tabs.component';
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
    MatProgressSpinnerModule,
    LaneTabsComponent,
    FilterBarComponent,
    ChampionCardComponent,
    InfoTooltipComponent,
  ],
  templateUrl: './results-page.component.html',
  styleUrl: './results-page.component.css',
})
export class ResultsPageComponent implements OnInit, OnDestroy {
  readonly destroy$ = new Subject<void>();
  readonly laneOrder: Lane[] = [...LANE_OPTIONS];

  isLoading = true;
  errorMessage = '';
  availableLanes: Lane[] = [...LANE_OPTIONS];
  champions: Champion[] = [];
  difficultyFilter: DifficultyFilter = 'all';

  query: {
    region: Region;
    tier: Tier;
    window: WindowKey;
    lane: Lane;
    sort: SortOption;
  } = {
    region: 'na',
    tier: 'diamond_plus',
    window: '7d',
    lane: 'top',
    sort: 'tier',
  };

  private dataset: TierlistDataset | null = null;
  private datasetKey = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly router: Router,
    private readonly tierlistService: TierlistService,
  ) {}

  ngOnInit(): void {
    this.route.queryParamMap.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      const region = this.readParam(params.get('region'), REGION_OPTIONS, 'na');
      const tier = this.readParam(params.get('tier'), TIER_OPTIONS, 'diamond_plus');
      const window = this.readParam(params.get('window'), WINDOW_OPTIONS, '7d');
      const lane = this.readParam(params.get('lane'), LANE_OPTIONS, 'top');
      const sort = this.readParam<SortOption>(params.get('sort'), ['tier', 'win_rate', 'pick_rate', 'difficulty'] as const, 'tier');

      this.query = { region, tier, window, lane, sort };

      const nextKey = `${region}:${tier}:${window}`;
      if (nextKey !== this.datasetKey) {
        this.loadDataset(nextKey);
        return;
      }

      this.refreshView();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
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

  trackByChampion(_index: number, champion: Champion): string {
    return champion.name;
  }

  private loadDataset(nextKey: string): void {
    this.datasetKey = nextKey;
    this.dataset = null;
    this.champions = [];
    this.errorMessage = '';
    this.isLoading = true;

    this.tierlistService
      .getDataset(this.query.region, this.query.tier, this.query.window)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (dataset) => {
          this.dataset = dataset;
          this.availableLanes = this.laneOrder.filter((lane) => Array.isArray(dataset.data[lane]));
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
          this.errorMessage = 'No se pudo cargar el dataset para la seleccion actual.';
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
        next.sort((a, b) => (a.filtered_rank ?? a.rank ?? 999) - (b.filtered_rank ?? b.rank ?? 999));
        break;
    }

    this.champions = next;
  }

  private updateQuery(update: Partial<Record<'lane' | 'sort', string>>): void {
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





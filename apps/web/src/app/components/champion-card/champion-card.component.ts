import { CommonModule } from '@angular/common';
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { RankedIconComponent } from '../ranked-icon/ranked-icon.component';

import { LANE_LABELS, ProductMode } from '../../core/models/selection.model';
import { Champion, Lane, SortOption } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-champion-card',
  imports: [CommonModule, RankedIconComponent],
  templateUrl: './champion-card.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './champion-card.component.css',
})
export class ChampionCardComponent {
  private static nextDetailsPanelId = 0;
  readonly detailsPanelId = `champion-details-${ChampionCardComponent.nextDetailsPanelId++}`;
  detailsOpen = false;

  @Input({ required: true }) champion!: Champion;
  @Input() mode: ProductMode = 'solo';
  @Input() lane: Lane = 'top';
  @Input() canonical = false;
  @Input() sort: SortOption = 'tier';
  @Input() banPriority: number | null = null;

  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';
  readonly laneLabels = LANE_LABELS;

  get primaryRank(): number | string {
    if (this.mode === 'teamplay') {
      return this.champion.teamplay_rank ?? this.champion.filtered_rank ?? this.champion.rank ?? '—';
    }

    return this.champion.filtered_rank ?? this.champion.rank ?? '—';
  }

  get visibleBadges(): string[] {
    return (this.champion.badges ?? []).slice(0, 3);
  }

  formatPercent(value: number | null | undefined): string {
    return value === null || value === undefined ? '—' : `${value.toFixed(1)}%`;
  }

  formatNumber(value: number | null | undefined): string {
    return value === null || value === undefined ? '—' : value.toFixed(1);
  }

}

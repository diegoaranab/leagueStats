import { CommonModule } from '@angular/common';
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';

import { LANE_LABELS, ProductMode } from '../../core/models/selection.model';
import { Champion, SortOption } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-champion-card',
  imports: [CommonModule, MatButtonModule],
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
  @Input() canonical = false;
  @Input() sort: SortOption = 'tier';
  @Input() banPriority: number | null = null;

  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';
  readonly laneLabels = LANE_LABELS;

  get primaryRank(): number | string {
    if (this.mode === 'teamplay') {
      return this.champion.teamplay_rank ?? this.champion.filtered_rank ?? this.champion.rank ?? '--';
    }

    return this.champion.filtered_rank ?? this.champion.rank ?? '--';
  }

  get visibleBadges(): string[] {
    return (this.champion.badges ?? []).slice(0, 3);
  }

  formatPercent(value: number | null | undefined): string {
    return value === null || value === undefined ? '--' : `${value.toFixed(1)}%`;
  }

  formatNumber(value: number | null | undefined): string {
    return value === null || value === undefined ? '--' : value.toFixed(1);
  }

  isGoldBadge(badge: string): boolean {
    return badge === 'High Pro Presence' || badge === 'Draft Priority';
  }

  isBlueBadge(badge: string): boolean {
    return badge === 'Flex Pick' || badge === 'Strong in Solo';
  }
}

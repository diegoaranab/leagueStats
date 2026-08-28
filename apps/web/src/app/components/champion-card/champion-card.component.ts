import { CommonModule, NgStyle } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

import { LANE_LABELS, ProductMode } from '../../core/models/selection.model';
import { Champion } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-champion-card',
  imports: [CommonModule, NgStyle, MatButtonModule, MatCardModule],
  templateUrl: './champion-card.component.html',
  styleUrl: './champion-card.component.css',
})
export class ChampionCardComponent {
  @Input({ required: true }) champion!: Champion;
  @Input() mode: ProductMode = 'solo';

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

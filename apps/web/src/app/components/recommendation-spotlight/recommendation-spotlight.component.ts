import { CommonModule, NgStyle } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';

import { LANE_LABELS, ProductMode } from '../../core/models/selection.model';
import { Champion, DifficultyFilter } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-recommendation-spotlight',
  imports: [CommonModule, NgStyle, MatButtonModule],
  templateUrl: './recommendation-spotlight.component.html',
  styleUrl: './recommendation-spotlight.component.css',
})
export class RecommendationSpotlightComponent {
  @Input({ required: true }) champion!: Champion;
  @Input({ required: true }) canonicalRank!: number;
  @Input() mode: ProductMode = 'solo';
  @Input() difficultyFilter: DifficultyFilter = 'all';

  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';
  readonly laneLabels = LANE_LABELS;

  get explanation(): string {
    const difficulty = this.difficultyFilter === 'easy'
      || this.difficultyFilter === 'medium'
      || this.difficultyFilter === 'hard'
      ? `${this.toTitleCase(this.difficultyFilter)} `
      : '';
    const mode = this.mode === 'teamplay' ? 'Flex / Clash' : 'Solo Queue';

    return `Top-ranked ${difficulty}${mode} option for this lane and context.`;
  }

  formatPercent(value: number | null | undefined): string {
    return value === null || value === undefined ? '--' : `${value.toFixed(1)}%`;
  }

  private toTitleCase(value: string): string {
    return value.charAt(0).toUpperCase() + value.slice(1);
  }
}

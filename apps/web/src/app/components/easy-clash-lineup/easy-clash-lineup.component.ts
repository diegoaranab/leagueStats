import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';

import { LANE_LABELS } from '../../core/models/selection.model';
import {
  EasyClashLineupResult,
  EasyClashLineupSlot,
} from '../../core/utils/easy-clash-lineup';

@Component({
  selector: 'app-easy-clash-lineup',
  imports: [CommonModule, MatButtonModule],
  templateUrl: './easy-clash-lineup.component.html',
  styleUrl: './easy-clash-lineup.component.css',
})
export class EasyClashLineupComponent {
  @Input({ required: true }) lineup!: EasyClashLineupResult;
  @Input() expanded = false;
  @Output() readonly expandedChange = new EventEmitter<boolean>();

  readonly laneLabels = LANE_LABELS;
  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';

  toggleExpanded(): void {
    this.expandedChange.emit(!this.expanded);
  }

  trackByLane(_index: number, slot: EasyClashLineupSlot): string {
    return slot.lane;
  }

  get unavailableMessage(): string {
    if (this.lineup.available) {
      return '';
    }

    if (this.lineup.reason === 'missing-role') {
      const labels = this.lineup.missingLanes.map((lane) => this.laneLabels[lane]);
      return `No eligible Easy candidate is available for ${labels.join(', ')}.`;
    }

    if (this.lineup.reason === 'not-enough-unique-champions') {
      return `Only ${this.lineup.uniqueCandidateCount} unique Easy champions are available across the five roles.`;
    }

    return 'The available Easy candidates overlap too heavily to fill all five roles uniquely.';
  }
}

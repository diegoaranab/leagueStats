import { Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatButtonToggleModule } from '@angular/material/button-toggle';

import { LANE_OPTIONS, Lane } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-lane-tabs',
  imports: [NgFor, MatButtonToggleModule],
  templateUrl: './lane-tabs.component.html',
  styleUrl: './lane-tabs.component.css',
})
export class LaneTabsComponent {
  @Input() lanes: Lane[] = [...LANE_OPTIONS];
  @Input() selectedLane: Lane = 'top';
  @Output() laneChange = new EventEmitter<Lane>();

  laneLabel(lane: Lane): string {
    const map: Record<Lane, string> = {
      top: 'Top',
      jungle: 'Jungla',
      middle: 'Mid',
      bottom: 'ADC',
      support: 'Support',
    };
    return map[lane];
  }
}

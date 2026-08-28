import { Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatButtonToggleModule } from '@angular/material/button-toggle';

import { LANE_LABELS } from '../../core/models/selection.model';
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
  @Input() laneCounts: Partial<Record<Lane, number>> = {};
  @Output() laneChange = new EventEmitter<Lane>();

  readonly laneLabels = LANE_LABELS;
}

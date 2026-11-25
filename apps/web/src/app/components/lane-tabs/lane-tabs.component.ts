import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';

import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { RankedIconComponent } from '../ranked-icon/ranked-icon.component';

import { LANE_LABELS } from '../../core/models/selection.model';
import { LANE_OPTIONS, Lane } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-lane-tabs',
  imports: [MatButtonToggleModule, RankedIconComponent],
  templateUrl: './lane-tabs.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './lane-tabs.component.css',
})
export class LaneTabsComponent {
  @Input() lanes: Lane[] = [...LANE_OPTIONS];
  @Input() selectedLane: Lane = 'top';
  @Input() laneCounts: Partial<Record<Lane, number>> = {};
  @Output() laneChange = new EventEmitter<Lane>();

  readonly laneLabels = LANE_LABELS;
}

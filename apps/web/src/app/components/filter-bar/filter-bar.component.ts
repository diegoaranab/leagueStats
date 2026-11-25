
import { Component, EventEmitter, Input, Output, ChangeDetectionStrategy } from '@angular/core';
import { MatSelectModule } from '@angular/material/select';

import { RankedIconComponent } from '../ranked-icon/ranked-icon.component';
import { ModeSelectorComponent } from '../mode-selector/mode-selector.component';
import {
  ProductMode,
  REGION_LABELS,
  TIER_LABELS,
  WINDOW_LABELS,
} from '../../core/models/selection.model';
import { REGION_OPTIONS, Region, TIER_OPTIONS, Tier, WINDOW_OPTIONS, WindowKey } from '../../core/models/tierlist.model';
import { DifficultyFilter, SortOption } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-filter-bar',
  imports: [
    RankedIconComponent,
    MatSelectModule,
    ModeSelectorComponent,
  ],
  templateUrl: './filter-bar.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './filter-bar.component.css',
})
export class FilterBarComponent {
  showDifficultyHelp = false;
  @Input() mode: ProductMode = 'solo';
  @Input() region: Region = 'na';
  @Input() tier: Tier = 'diamond';
  @Input() window: WindowKey = '7d';
  @Input() sort: SortOption = 'tier';
  @Input() difficultyFilter: DifficultyFilter = 'all';

  @Output() modeChange = new EventEmitter<ProductMode>();
  @Output() regionChange = new EventEmitter<Region>();
  @Output() tierChange = new EventEmitter<Tier>();
  @Output() windowChange = new EventEmitter<WindowKey>();
  @Output() sortChange = new EventEmitter<SortOption>();
  @Output() difficultyChange = new EventEmitter<DifficultyFilter>();
  @Output() closeRequested = new EventEmitter<void>();

  readonly regionOptions = REGION_OPTIONS;
  readonly tierOptions = TIER_OPTIONS;
  readonly windowOptions = WINDOW_OPTIONS;
  readonly regionLabels = REGION_LABELS;
  readonly tierLabels = TIER_LABELS;
  readonly windowLabels = WINDOW_LABELS;
}

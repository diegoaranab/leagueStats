
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';

import { RankedIconComponent } from '../ranked-icon/ranked-icon.component';
import { LANE_LABELS, ProductMode } from '../../core/models/selection.model';
import { Champion, Lane } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-recommended-bans',
  imports: [RankedIconComponent],
  templateUrl: './recommended-bans.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './recommended-bans.component.css',
})
export class RecommendedBansComponent {
  @Input() mode: ProductMode = 'solo';
  @Input() lane: Lane = 'top';
  @Input() difficultyFiltered = false;
  @Input() champions: Champion[] = [];

  readonly laneLabels = LANE_LABELS;
  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';

}

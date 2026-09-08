import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

import { ProductMode } from '../../core/models/selection.model';
import { Champion } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-recommended-bans',
  imports: [CommonModule],
  templateUrl: './recommended-bans.component.html',
  styleUrl: './recommended-bans.component.css',
})
export class RecommendedBansComponent {
  @Input() mode: ProductMode = 'solo';
  @Input() champions: Champion[] = [];

  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';

  trackByChampion(_index: number, champion: Champion): string {
    return champion.name;
  }
}

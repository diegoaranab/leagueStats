import { CommonModule, NgStyle } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';

import { Champion } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-champion-card',
  imports: [
    CommonModule,
    NgStyle,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatExpansionModule,
    MatIconModule,
  ],
  templateUrl: './champion-card.component.html',
  styleUrl: './champion-card.component.css',
})
export class ChampionCardComponent {
  @Input({ required: true }) champion!: Champion;

  readonly fallbackIcon = 'https://ddragon.leagueoflegends.com/cdn/14.1.1/img/champion/Aatrox.png';
}

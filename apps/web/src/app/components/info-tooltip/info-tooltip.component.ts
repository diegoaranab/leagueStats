import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-info-tooltip',
  imports: [MatButtonModule, MatTooltipModule],
  templateUrl: './info-tooltip.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './info-tooltip.component.css',
})
export class InfoTooltipComponent {
  @Input() text = 'Difficulty is relative to the selected mode, rank, region, window, and lane pool.';
}

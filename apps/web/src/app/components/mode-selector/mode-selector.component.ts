import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { MODE_DETAILS, PRODUCT_MODE_OPTIONS, ProductMode } from '../../core/models/selection.model';

@Component({
  selector: 'app-mode-selector',
  imports: [CommonModule],
  templateUrl: './mode-selector.component.html',
  styleUrl: './mode-selector.component.css',
})
export class ModeSelectorComponent {
  @Input() selectedMode: ProductMode = 'solo';
  @Input() variant: 'feature' | 'compact' = 'feature';

  @Output() modeChange = new EventEmitter<ProductMode>();

  readonly modes = PRODUCT_MODE_OPTIONS;
  readonly modeDetails = MODE_DETAILS;
}

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { DifficultyFilter, SortOption } from '../../core/models/tierlist.model';

@Component({
  selector: 'app-filter-bar',
  imports: [CommonModule, MatCardModule, MatChipsModule, MatFormFieldModule, MatSelectModule],
  templateUrl: './filter-bar.component.html',
  styleUrl: './filter-bar.component.css',
})
export class FilterBarComponent {
  @Input() region = 'na';
  @Input() tier = 'diamond_plus';
  @Input() window = '7d';
  @Input() sort: SortOption = 'tier';
  @Input() difficultyFilter: DifficultyFilter = 'all';

  @Output() sortChange = new EventEmitter<SortOption>();
  @Output() difficultyChange = new EventEmitter<DifficultyFilter>();
}

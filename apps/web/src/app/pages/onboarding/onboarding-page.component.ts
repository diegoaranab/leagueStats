import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { ModeSelectorComponent } from '../../components/mode-selector/mode-selector.component';
import {
  DEFAULT_RESULTS_QUERY,
  ProductMode,
  REGION_LABELS,
  TIER_LABELS,
  WINDOW_LABELS,
} from '../../core/models/selection.model';
import {
  REGION_OPTIONS,
  Region,
  TIER_OPTIONS,
  Tier,
  WINDOW_OPTIONS,
  WindowKey,
} from '../../core/models/tierlist.model';

@Component({
  selector: 'app-onboarding-page',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    ModeSelectorComponent,
  ],
  templateUrl: './onboarding-page.component.html',
  styleUrl: './onboarding-page.component.css',
})
export class OnboardingPageComponent {
  readonly regionOptions = REGION_OPTIONS;
  readonly tierOptions = TIER_OPTIONS;
  readonly windowOptions = WINDOW_OPTIONS;
  readonly regionLabels = REGION_LABELS;
  readonly tierLabels = TIER_LABELS;
  readonly windowLabels = WINDOW_LABELS;
  readonly form = this.formBuilder.group({
    mode: this.formBuilder.control<ProductMode>(DEFAULT_RESULTS_QUERY.mode, Validators.required),
    tier: this.formBuilder.control<Tier>(DEFAULT_RESULTS_QUERY.tier, Validators.required),
    region: this.formBuilder.control<Region>(DEFAULT_RESULTS_QUERY.region, Validators.required),
    window: this.formBuilder.control<WindowKey>(DEFAULT_RESULTS_QUERY.window, Validators.required),
  });

  constructor(
    private readonly formBuilder: NonNullableFormBuilder,
    private readonly router: Router,
  ) {}

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const { mode, tier, region, window } = this.form.getRawValue();
    this.router.navigate(['/results'], {
      queryParams: {
        mode,
        tier,
        region,
        window,
        lane: DEFAULT_RESULTS_QUERY.lane,
        sort: DEFAULT_RESULTS_QUERY.sort,
      },
    });
  }
}

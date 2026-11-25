
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { readResultsQuery } from '../../core/models/results-query';
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
    ReactiveFormsModule,
    MatSelectModule,
    ModeSelectorComponent,
  ],
  templateUrl: './onboarding-page.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './onboarding-page.component.css',
})
export class OnboardingPageComponent {
  // Illustrative LoLalytics snapshot, November 22, 2026. Results always load the selected dataset.
  readonly examplePicks = [
    { name: 'Darius', portrait: 'darius', winRate: '52.8%' },
    { name: 'Akali', portrait: 'akali', winRate: '52.3%' },
    { name: 'Irelia', portrait: 'irelia', winRate: '53.4%' },
  ];
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
    private readonly route: ActivatedRoute,
  ) {
    this.route.queryParamMap.pipe(takeUntilDestroyed()).subscribe(params => {
      const { mode, tier, region, window } = readResultsQuery(params);
      this.form.setValue({ mode, tier, region, window });
    });
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const { mode, tier, region, window } = this.form.getRawValue();
    this.router.navigate(['/results'], {
      queryParams: {
        ...readResultsQuery(this.route.snapshot.queryParamMap),
        mode,
        tier,
        region,
        window,
      },
    });
  }
}

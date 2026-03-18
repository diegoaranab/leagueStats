import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

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
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './onboarding-page.component.html',
  styleUrl: './onboarding-page.component.css',
})
export class OnboardingPageComponent {
  readonly regionOptions = REGION_OPTIONS;
  readonly tierOptions = TIER_OPTIONS;
  readonly windowOptions = WINDOW_OPTIONS;

  readonly form = this.formBuilder.group({
    tier: this.formBuilder.control<Tier>('diamond_plus', Validators.required),
    region: this.formBuilder.control<Region>('na', Validators.required),
    window: this.formBuilder.control<WindowKey>('7d', Validators.required),
  });

  constructor(
    private readonly formBuilder: NonNullableFormBuilder,
    private readonly router: Router,
  ) {}

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const { tier, region, window } = this.form.getRawValue();
    this.router.navigate(['/results'], {
      queryParams: {
        tier,
        region,
        window,
        lane: 'top',
        sort: 'tier',
      },
    });
  }
}

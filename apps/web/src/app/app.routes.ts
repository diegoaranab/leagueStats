import { Routes } from '@angular/router';

import { OnboardingPageComponent } from './pages/onboarding/onboarding-page.component';
import { ResultsPageComponent } from './pages/results/results-page.component';

export const routes: Routes = [
  {
    path: '',
    component: OnboardingPageComponent,
  },
  {
    path: 'results',
    component: ResultsPageComponent,
  },
  {
    path: '**',
    redirectTo: '',
  },
];

## UI Pro Max Stack Guidelines
**Stack:** angular | **Query:** material design theme
**Source:** stacks/angular.csv | **Found:** 1 results

### Result 1
- **Category:** Styling
- **Guideline:** Use Angular Material theming tokens
- **Description:** Material 3 uses design tokens for systematic theming
- **Do:** M3 token-based theming for Angular Material
- **Don't:** Overriding Angular Material CSS with deep selectors
- **Code Good:** @include mat.button-theme($my-theme)
- **Code Bad:** ::ng-deep .mat-button { background: red }
- **Severity:** Medium
- **Docs URL:** https://material.angular.io/guide/theming
- **Applies To:** angular 22.x
- **Status:** active
- **Verified At:** 2026-08-13


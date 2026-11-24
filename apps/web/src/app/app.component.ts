import { Component, ChangeDetectionStrategy, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, PRIMARY_OUTLET, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';
import { readResultsQuery } from './core/models/results-query';
import { DEFAULT_RESULTS_QUERY, MODE_DETAILS, PRODUCT_MODE_OPTIONS, ProductMode, ResultsQuery } from './core/models/selection.model';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './app.component.css',
})
export class AppComponent {
  private readonly router = inject(Router);
  private readonly url = toSignal(this.router.events.pipe(
    filter((event) => event instanceof NavigationEnd),
    map((event) => event.urlAfterRedirects),
  ), { initialValue: this.router.url });

  readonly resultsContext = computed(() => {
    const url = this.router.parseUrl(this.url());
    return url.root.children[PRIMARY_OUTLET]?.segments[0]?.path === 'results'
      ? readResultsQuery(url.queryParamMap)
      : null;
  });

  readonly modes = PRODUCT_MODE_OPTIONS;
  readonly modeDetails = MODE_DETAILS;
  readonly routeMatchOptions = { paths: 'exact', queryParams: 'ignored', fragment: 'ignored', matrixParams: 'ignored' } as const;

  queueQuery(query: ResultsQuery, mode: ProductMode): ResultsQuery {
    return query.mode === mode ? query : { ...query, mode, sort: DEFAULT_RESULTS_QUERY.sort };
  }

  skipToMain(main: HTMLElement): void {
    main.focus({ preventScroll: true });
    main.scrollIntoView({ block: 'start', behavior: 'instant' });
  }
}

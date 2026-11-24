import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatToolbarModule } from '@angular/material/toolbar';

@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    MatButtonModule,
    MatToolbarModule,
  ],
  templateUrl: './app.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './app.component.css',
})
export class AppComponent {
  readonly routeMatchOptions = { paths: 'exact', queryParams: 'ignored', fragment: 'ignored', matrixParams: 'ignored' } as const;

  skipToMain(main: HTMLElement): void {
    main.focus({ preventScroll: true });
    const toolbarHeight = main.closest('.app-shell')?.querySelector('.topbar')?.getBoundingClientRect().height ?? 0;
    const top = main.getBoundingClientRect().top + window.scrollY - toolbarHeight - 8;
    window.scrollTo({ top: Math.max(0, top), behavior: 'instant' });
  }
}

import { ChangeDetectionStrategy, Component, input } from '@angular/core';

const PATHS = {
  chevron: 'm9 5 7 7-7 7',
  down: 'm6 9 6 6 6-6',
  check: 'm5 12 4 4L19 6',
  top: 'M5 19V5h14M19 9v10H9',
  jungle: 'm12 3 6 8-6 10-6-10Zm0 0v18',
  middle: 'M5 19 19 5M5 12V5h7m0 14h7v-7',
  bottom: 'M19 5v14H5M5 15V5h10',
  support: 'm3 8 6 2 3-5 3 5 6-2-4 7-5 4-5-4Z',
  ban: 'M6.3 6.3l11.4 11.4M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  lineup: 'M4 7h16M4 12h16M4 17h16',
  warning: 'M12 8v5m0 3v.1M3 19 12 4l9 15Z',
  sliders: 'M4 7h16M4 17h16M8 4v6m8 4v6',
  close: 'm6 6 12 12M18 6 6 18',
  info: 'M12 11v5m0-8v.1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z',
} as const;

@Component({
  selector: 'app-ranked-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { 'aria-hidden': 'true' },
  styles: ':host { display: inline-flex; flex: none; }',
  template: '<svg class="ranked-icon" viewBox="0 0 24 24"><path [attr.d]="paths[name()]"/></svg>',
})
export class RankedIconComponent {
  readonly name = input.required<keyof typeof PATHS>();
  readonly paths = PATHS;
}

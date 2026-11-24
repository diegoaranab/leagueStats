"""Results filter behavior, keyboard, and reflow against the Pages artifact."""
import functools
import http.server
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_BASE_URL = os.environ.get('RESULTS_CONTROLS_TEST_URL', '').strip()
RESULT_QUERY = '?mode=solo&region=lan&tier=gold&window=14d&lane=top&sort=win_rate&difficulty=hard'


def results_test_url(base_url):
    return f"{base_url.rstrip('/')}/results/{RESULT_QUERY}"


def run():
    server = None
    if EXTERNAL_BASE_URL:
        base_url = EXTERNAL_BASE_URL.rstrip('/')
        parsed = urlparse(base_url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('RESULTS_CONTROLS_TEST_URL must be an absolute HTTP(S) URL')
        target = base_url
    else:
        tmp = tempfile.TemporaryDirectory()
        os.symlink(ROOT / 'dist/web/browser', Path(tmp.name) / 'leagueStats', target_is_directory=True)

        class PagesArtifactHandler(http.server.SimpleHTTPRequestHandler):
            def send_head(self):
                requested = self.path.split('?', 1)[0]
                if requested.startswith('/leagueStats/') and not Path(self.translate_path(requested)).exists():
                    self.path = '/leagueStats/index.html'
                return super().send_head()

        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0),
            functools.partial(PagesArtifactHandler, directory=tmp.name),
        )
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base_url = f'http://127.0.0.1:{server.server_port}/leagueStats'
        target = base_url

    print(f'Results controls browser target: {target}')
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.route('**/data/**/*.json', lambda route: route.fulfill(json=fixture('test')[1 if '/teamplay/' in route.request.url else 0]))
            page.goto(results_test_url(base_url))
            expect(page.locator('h1')).to_be_focused()
            trigger = page.get_by_role('button', name='Filters', exact=True)
            drawer = page.get_by_role('dialog', name='Refine results')
            trigger.click()
            heading = drawer.get_by_role('heading', name='Refine results')
            expect(heading).to_be_focused()
            assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle !== 'none'")
            expect(drawer).to_be_visible()
            assert page.evaluate("document.querySelector('mat-drawer').getAttribute('aria-modal')") is None
            assert heading.bounding_box()['y'] >= page.locator('.topbar').bounding_box()['height']
            page.screenshot(path='/tmp/results-controls-390-drawer-open.png', animations='disabled')
            expect(drawer.get_by_role('combobox', name='Region')).to_contain_text('Latin America North')
            expect(drawer.get_by_role('combobox', name='Window')).to_contain_text('Last 14 Days')

            # Material/CDK focus trap must cycle only through the open drawer's actions.
            keyboard_targets = []
            visited = set()
            for _ in range(30):
                page.keyboard.press('Tab')
                focus = page.evaluate("""() => {
                  const el = document.activeElement;
                  return {
                    inside: document.querySelector('mat-drawer').contains(el),
                    marker: el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.textContent.trim() || el.tagName,
                  };
                }""")
                assert focus['inside'], f'Tab escaped the open drawer to {focus["marker"]}'
                marker = focus['marker']
                keyboard_targets.append(marker)
                if marker in visited:
                    break
                visited.add(marker)
            assert len(visited) >= 7, keyboard_targets
            actionable_count = drawer.locator('button:not([disabled]), [role="combobox"]').count()
            assert len(visited) >= actionable_count, (keyboard_targets, actionable_count)
            assert len(keyboard_targets) > len(visited), keyboard_targets

            # Reverse traversal wraps from the first action back to the last action.
            first_action = drawer.get_by_role('button', name='Close filters')
            first_action.focus()
            page.keyboard.press('Shift+Tab')
            assert page.evaluate("document.querySelector('mat-drawer').contains(document.activeElement)")
            reverse_targets = []
            reverse_seen = set()
            for _ in range(30):
                focus = page.evaluate("""() => {
                  const el = document.activeElement;
                  return {
                    inside: document.querySelector('mat-drawer').contains(el),
                    marker: el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.textContent.trim() || el.tagName,
                  };
                }""")
                assert focus['inside']
                marker = focus['marker']
                reverse_targets.append(marker)
                if marker in reverse_seen:
                    break
                reverse_seen.add(marker)
                page.keyboard.press('Shift+Tab')
                assert page.evaluate("document.querySelector('mat-drawer').contains(document.activeElement)")
            assert len(reverse_seen) >= 7, reverse_targets
            assert len(reverse_seen) >= actionable_count, (reverse_targets, actionable_count)

            # The scrim intercepts pointer input on the visible page behind this non-modal dialog.
            assert page.locator('.mat-drawer-backdrop').is_visible()
            change_setup = page.get_by_role('link', name='Change setup')
            blocked_point = change_setup.bounding_box()
            if blocked_point:
                x, y = blocked_point['x'] + blocked_point['width'] / 2, blocked_point['y'] + blocked_point['height'] / 2
                blocked = page.evaluate('''(p) => {
                  const target = document.elementFromPoint(p.x, p.y);
                  return !target?.closest('a[routerlink="/"]');
                }''', {'x': x, 'y': y})
                assert blocked, 'The open drawer does not block pointer access to the background action'

            with page.expect_response(lambda response: '/data/teamplay/' in response.url):
                drawer.locator('button.mode-option').filter(has_text='Flex / Clash').click()
            expect(page).to_have_url(re.compile('mode=teamplay'))
            expect(page.locator('.draft')).to_be_visible()
            controls = [('Region', 'Latin America South'), ('Rank', 'Diamond'), ('Window', 'Last 7 Days'), ('Sort by', 'Pick rate'), ('Difficulty', 'Easy')]
            for label, option in controls:
                drawer.get_by_role('combobox', name=label).click()
                if label in ('Region', 'Rank', 'Window'):
                    with page.expect_response(lambda response: '/data/teamplay/' in response.url):
                        page.get_by_role('option', name=option, exact=True).click()
                else:
                    page.get_by_role('option', name=option, exact=True).click()
                expect(drawer.get_by_role('combobox', name=label)).to_contain_text(option)
                expect(page.locator('.draft')).to_be_visible()
                expect(drawer).to_be_visible()

            help_button = drawer.get_by_role('button', name='About difficulty')
            help_button.click()
            expect(drawer.get_by_text('Difficulty is relative', exact=False)).to_be_visible()
            page.screenshot(path='/tmp/results-controls-390-help-expanded.png', animations='disabled')
            help_button.focus()
            page.keyboard.press('Enter')
            expect(help_button).to_have_attribute('aria-expanded', 'false')
            page.keyboard.press('Enter')
            expect(drawer.get_by_text('Difficulty is relative', exact=False)).to_be_visible()

            drawer.get_by_role('button', name='Close filters').click()
            expect(trigger).to_be_focused()
            expect(drawer).to_be_hidden()
            page.screenshot(path='/tmp/results-controls-390-drawer-closed.png', animations='disabled')
            expect(page.locator('.context-line')).to_contain_text('Sort: Pick rate')
            expect(page.locator('.context-line')).to_contain_text('Difficulty: Easy')
            expect(page.get_by_role('radiogroup', name='Choose a lane')).to_be_visible()
            trigger.click()
            expect(heading).to_be_focused()
            page.keyboard.press('Escape')
            expect(trigger).to_be_focused()
            trigger.click()
            expect(heading).to_be_focused()
            page.locator('.mat-drawer-backdrop').click(position={'x': 370, 'y': 150})
            expect(trigger).to_be_focused()

            for width, height in [(320,568),(390,844),(844,390),(1080,768),(1081,768),(1200,800),(1366,768),(1920,1080)]:
                page.set_viewport_size({'width': width, 'height': height})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, height)
            page.set_viewport_size({'width': 1366, 'height': 768})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path='/tmp/results-controls-desktop-200-text.png')
            page.evaluate("document.documentElement.style.fontSize = ''")

            # Restore long representative values before capturing the desktop evidence.
            page.goto(results_test_url(base_url))
            expect(page.locator('.champion-card').first).to_be_visible()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            trigger = page.get_by_role('button', name='Filters', exact=True)
            trigger.click()
            expect(drawer).to_be_visible()
            page.wait_for_timeout(350)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            region_value = drawer.get_by_role('combobox', name='Region').locator('.mat-mdc-select-value-text')
            window_value = drawer.get_by_role('combobox', name='Window').locator('.mat-mdc-select-value-text')
            assert region_value.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
            assert region_value.evaluate('(el) => el.scrollHeight <= el.clientHeight + 1')
            assert window_value.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
            assert window_value.evaluate('(el) => el.scrollHeight <= el.clientHeight + 1')
            page.screenshot(path='/tmp/results-controls-390-200-text-drawer.png', animations='disabled')
            drawer.get_by_role('button', name='Close filters').click()
            expect(trigger).to_be_focused()
            expect(drawer).to_be_hidden()
            page.evaluate("document.documentElement.style.fontSize = ''")

            page.set_viewport_size({'width': 1366, 'height': 768})
            page.wait_for_timeout(250)
            old_layout = page.add_style_tag(content="""
              .bar:not(.bar--drawer) { align-items: flex-start !important; flex-wrap: wrap !important; }
              .bar:not(.bar--drawer) .filter-group { flex-basis: 310px !important; }
              .control-grid { display: grid !important; grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr)) !important; gap: .65rem !important; flex: 1 1 760px !important; }
              .control-grid mat-form-field { min-width: 0 !important; }
              .difficulty-control { display: grid !important; grid-template-columns: 1fr !important; align-content: start !important; }
              .difficulty-help { width: auto !important; height: auto !important; min-height: 44px !important; justify-self: start !important; }
            """)
            before = page.evaluate("""() => {
              const filters = document.querySelector('.results-shell__content app-filter-bar');
              const firstPick = document.querySelector('.champion-card');
              return {filterHeight: Math.round(filters.getBoundingClientRect().height), firstRankedY: Math.round(firstPick.getBoundingClientRect().y)};
            }""")
            old_layout.evaluate('(el) => el.remove()')
            metrics = page.evaluate("""() => {
              const filters = document.querySelector('.results-shell__content app-filter-bar');
              const firstPick = document.querySelector('.champion-card');
              return {filterHeight: Math.round(filters.getBoundingClientRect().height), firstRankedY: Math.round(firstPick.getBoundingClientRect().y)};
            }""")
            print(f"1366x768 before correction: filter panel {before['filterHeight']}px; first ranked row y={before['firstRankedY']}px")
            print(f"1366x768 after correction: filter panel {metrics['filterHeight']}px; first ranked row y={metrics['firstRankedY']}px")
            page.screenshot(path='/tmp/results-controls-1366-desktop.png', animations='disabled')
            for label in ('Region', 'Window'):
                control = page.locator('.results-shell__content app-filter-bar').get_by_role('combobox', name=label)
                value = control.locator('.mat-mdc-select-value-text')
                assert value.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                assert value.evaluate('(el) => el.scrollHeight <= el.clientHeight + 1')

            help_button = page.locator('.results-shell__content app-filter-bar').get_by_role('button', name='About difficulty')
            help_button.click()
            expect(page.locator('.results-shell__content app-filter-bar .difficulty-explanation')).to_be_visible()
            page.screenshot(path='/tmp/results-controls-1366-help-expanded.png', animations='disabled')
            help_button.click()
            page.set_viewport_size({'width': 1920, 'height': 1080})
            page.screenshot(path='/tmp/results-controls-1920-desktop.png', animations='disabled')
            page.set_viewport_size({'width': 1081, 'height': 768})
            page.screenshot(path='/tmp/results-controls-1081-desktop.png', animations='disabled')

            page.set_viewport_size({'width': 390, 'height': 844})
            trigger.click()
            expect(heading).to_be_focused()
            page.set_viewport_size({'width': 1366, 'height': 768})
            expect(drawer).to_be_hidden()
            expect(page.locator('h1')).to_be_focused()
            browser.close()
    finally:
        if server:
            server.shutdown()
        if 'tmp' in locals():
            tmp.cleanup()


if __name__ == '__main__':
    run()

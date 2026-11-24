"""Exercise Home setup against the Pages artifact or HOME_SETUP_TEST_URL."""
import functools
import http.server
import os
from pathlib import Path
import re
import tempfile
import threading
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]


def run():
    external = os.environ.get('HOME_SETUP_TEST_URL')
    with tempfile.TemporaryDirectory() as tmp:
        server = None
        if external:
            base = external.rstrip('/')
        else:
            os.symlink(ROOT / 'dist/web/browser', Path(tmp) / 'leagueStats', target_is_directory=True)
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}/leagueStats'
        print('Home setup target:', base, flush=True)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={'width': 390, 'height': 844})
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=fixture('test')[1 if '/teamplay/' in route.request.url else 0]))
                for width, height in [(320, 568), (390, 844), (430, 932), (768, 1024), (1366, 768), (1920, 1080), (844, 390)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(base + '/')
                    page.evaluate('document.fonts.ready')
                    boxes = page.locator('.mode-option').evaluate_all('(els) => els.map(e => {let r=e.getBoundingClientRect(); return {top:r.top,bottom:r.bottom,left:r.left,right:r.right}})')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    if width in (320, 390):
                        assert all(r['top'] >= 0 and r['bottom'] <= height and r['left'] >= 0 and r['right'] <= width for r in boxes), boxes
                    if width == 390:
                        assert page.locator('.cta-button').evaluate('(e) => e.getBoundingClientRect().bottom <= innerHeight')
                        assert all(page.get_by_role('combobox', name=n).evaluate('(e) => e.getBoundingClientRect().bottom <= innerHeight') for n in ('Region', 'Rank', 'Window'))
                    page.screenshot(path=f'/tmp/home-after-{width}x{height}.png', full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(base + '/')
                expect(page.get_by_role('group', name='Queue')).to_be_visible()
                solo = page.get_by_role('button', name=re.compile('Solo Queue'))
                flex = page.locator('.mode-option').nth(1)
                expect(solo).to_have_attribute('aria-pressed', 'true')
                expect(page.get_by_role('combobox', name='Region')).to_contain_text('North America')
                expect(page.get_by_role('combobox', name='Rank')).to_contain_text('Diamond')
                expect(page.get_by_role('combobox', name='Window')).to_contain_text('Last 7 Days')
                solo.focus(); page.keyboard.press('Tab')
                assert flex.evaluate('(e) => document.activeElement === e')
                page.keyboard.press('Space')
                expect(flex).to_have_attribute('aria-pressed', 'true')
                assert urlparse(page.url).path.rstrip('/').endswith('leagueStats') if not external else True
                page.screenshot(path='/tmp/home-flex-focus.png', full_page=True)
                for name, value in [('Region', 'Latin America North'), ('Rank', 'Gold'), ('Window', 'Last 14 Days')]:
                    page.get_by_role('combobox', name=name).click()
                    page.get_by_role('option', name=value, exact=True).click()
                    expect(page.get_by_role('combobox', name=name)).to_contain_text(value)
                page.screenshot(path='/tmp/home-long-values.png', full_page=True)
                page.get_by_role('button', name='View recommendations').click()
                expect(page.locator('h1')).to_have_text('Top picks')
                assert page.evaluate('document.activeElement.tagName') == 'H1'
                assert parse_qs(urlparse(page.url).query) == {'mode':['teamplay'], 'region':['lan'], 'tier':['gold'], 'window':['14d'], 'lane':['top'], 'sort':['tier'], 'difficulty':['all']}
                page.goto(base + '/results/?mode=teamplay&region=lan&tier=gold&window=14d&lane=middle&sort=win_rate&difficulty=hard')
                page.get_by_role('link', name='Change setup').click()
                expect(page.get_by_role('combobox', name='Region')).to_contain_text('Latin America North')
                page.get_by_role('combobox', name='Region').click()
                page.get_by_role('option', name='Latin America South').click()
                page.get_by_role('button', name=re.compile('Solo Queue')).click()
                page.get_by_role('button', name='View recommendations').click()
                expect(page.locator('h1')).to_have_text('Mid picks')
                assert parse_qs(urlparse(page.url).query) == {'mode':['solo'], 'region':['las'], 'tier':['gold'], 'window':['14d'], 'lane':['middle'], 'sort':['win_rate'], 'difficulty':['hard']}
                page.goto(base + '/')
                page.add_style_tag(content='html { font-size: 200% !important; }')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.get_by_role('combobox', name='Region').click()
                page.get_by_role('option', name='Latin America North').click()
                page.get_by_role('combobox', name='Window').click()
                page.get_by_role('option', name='Last 14 Days').click()
                for name in ('Region', 'Window'):
                    value = page.get_by_role('combobox', name=name).locator('.mat-mdc-select-value-text')
                    assert value.evaluate('(e) => e.scrollWidth <= e.clientWidth + 1'), name
                button = page.locator('.cta-button')
                assert button.evaluate('(e) => e.scrollHeight <= e.clientHeight + 1')
                page.wait_for_timeout(300)
                page.evaluate('window.scrollTo(0, 0)')
                page.screenshot(path='/tmp/home-after-390-200percent.png', full_page=True)
                browser.close()
        finally:
            if server:
                server.shutdown()


if __name__ == '__main__':
    run()

"""Focused accessibility checks against the local Pages artifact or explicit URL."""
import copy
import functools
import http.server
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]
QUERY = 'region=na&tier=gold&window=7d&lane=top&sort=tier&difficulty=all'


def run():
    external = os.environ.get('UI_POLISH_TEST_URL', '').strip()
    server = None
    with tempfile.TemporaryDirectory() as tmp:
        if external:
            parsed = urlparse(external)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                raise ValueError('UI_POLISH_TEST_URL must be an absolute HTTP(S) URL')
            base = external.rstrip('/')
        else:
            os.symlink(ROOT / 'dist/web/browser', Path(tmp) / 'leagueStats', target_is_directory=True)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}/leagueStats'
        print('UI accessibility polish target:', base, flush=True)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={'width': 1366, 'height': 768}, reduced_motion='reduce')
                solo, team = fixture('polish')
                solo['data']['jungle'] = solo['data']['jungle'][:1]
                team['data']['jungle'] = team['data']['jungle'][:1]
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=team if '/teamplay/' in route.request.url else solo))
                for label, path, current in [('home', '/', 'Home'), ('home-query', '/?mode=solo&' + QUERY, 'Home'), ('results', '/results/?mode=solo&' + QUERY, 'Results')]:
                    page.goto(base + path)
                    expect(page.locator('.toolbar-nav [aria-current="page"]')).to_have_count(1)
                    expect(page.locator('.toolbar-nav [aria-current="page"]')).to_have_text(current)
                    if label == 'home':
                        print('Navigation computed colors:', page.locator('.toolbar-nav .is-active').evaluate("e => { const s = getComputedStyle(e), t = getComputedStyle(document.querySelector('.topbar')); return {text: s.color, background: t.backgroundColor, indicator: s.boxShadow}; }"), flush=True)
                    page.screenshot(path=f'/tmp/ui-polish-after-{label}.png')
                for mode in ('solo', 'teamplay'):
                    page.goto(base + '/results/?mode=' + mode + '&' + QUERY)
                    expect(page.locator('h1')).to_be_focused()
                    cards = page.locator('.picks-list app-champion-card')
                    expect(cards).to_have_count(5)
                    expect(page.locator('.context-line')).to_contain_text('5 picks')
                    for card in cards.all()[:2]:
                        name = card.locator('h3').inner_text()
                        button = card.get_by_role('button', name='More details about ' + name, exact=True)
                        panel = page.locator('#' + button.get_attribute('aria-controls'))
                        expect(button).to_have_attribute('aria-expanded', 'false')
                        button.focus(); page.keyboard.press('Space')
                        expect(button).to_have_attribute('aria-expanded', 'true')
                        expect(panel).to_be_visible()
                        page.screenshot(path=f'/tmp/ui-polish-{mode}-details.png')
                        page.keyboard.press('Enter'); expect(panel).to_be_hidden()
                    page.get_by_role('radio', name='Jungle', exact=False).click()
                    expect(page.locator('.context-line')).to_contain_text('1 pick')
                    expect(page.get_by_role('radio', name='Jungle', exact=False)).to_contain_text('1 pick')
                    page.screenshot(path=f'/tmp/ui-polish-{mode}-one.png')
                    page.goto(base + '/results/?mode=' + mode + '&region=na&tier=gold&window=7d&lane=jungle&sort=tier&difficulty=easy')
                    expect(page.locator('.context-line')).to_contain_text('0 picks')
                    expect(page.get_by_role('radio', name='Jungle', exact=False)).to_contain_text('1 pick')
                for path in ('/', '/results/?mode=solo&' + QUERY, '/results/?mode=teamplay&' + QUERY):
                    page.goto(base + path)
                    if path.startswith('/results'):
                        expect(page.locator('h1')).to_be_focused()
                    page.evaluate("document.body.tabIndex = -1; document.body.focus(); document.body.removeAttribute('tabindex')")
                    page.keyboard.press('Tab')
                    skip = page.get_by_role('button', name='Skip to main content')
                    expect(skip).to_be_focused()
                    if path == '/':
                        print('Skip computed colors:', skip.evaluate("e => { const s = getComputedStyle(e); return {text: s.color, background: s.backgroundColor, border: s.borderColor, outline: s.outlineColor}; }"), flush=True)
                    page.wait_for_function("document.querySelector('.skip-link').getBoundingClientRect().top >= 0")
                    before = page.evaluate('({url: location.href, length: history.length})')
                    page.screenshot(path='/tmp/ui-polish-skip-focus.png')
                    page.keyboard.press('Enter')
                    expect(page.locator('main')).to_be_focused()
                    assert page.evaluate("document.querySelector('main').getBoundingClientRect().top >= document.querySelector('.topbar').getBoundingClientRect().bottom - 1")
                    assert before == page.evaluate('({url: location.href, length: history.length})')
                    page.screenshot(path='/tmp/ui-polish-skip-destination.png')
                    page.keyboard.press('Tab')
                    assert page.evaluate("document.querySelector('main').contains(document.activeElement)")
                    skip.focus(); skip.click()
                    expect(page.locator('main')).to_be_focused()
                    assert before == page.evaluate('({url: location.href, length: history.length})')
                for mode, source in (('solo', solo), ('teamplay', team)):
                    missing = copy.deepcopy(source)
                    del missing['data']['top']
                    page.unroute('**/data/**/*.json')
                    page.route('**/data/**/*.json', lambda route: route.fulfill(json=missing))
                    page.goto(base + '/results/?mode=' + mode + '&' + QUERY)
                    expect(page.get_by_role('status')).to_have_text('Selected lane unavailable')
                    expect(page.locator('.context-line')).not_to_contain_text('0 picks')
                    expect(page.get_by_role('radio', name='Top', exact=False)).to_have_count(0)
                    page.unroute('**/data/**/*.json')
                    page.route('**/data/**/*.json', lambda route: route.fulfill(status=404))
                    page.reload()
                    expect(page.get_by_role('status')).to_have_text('Dataset unavailable')
                    expect(page.locator('.context-line')).not_to_contain_text('0 picks')
                page.unroute('**/data/**/*.json')
                pending = []
                page.route('**/data/**/*.json', lambda route: pending.append(route))
                page.goto(base + '/results/?mode=solo&' + QUERY)
                expect(page.get_by_role('status')).to_contain_text('Loading')
                expect(page.locator('.context-line')).not_to_contain_text('0 picks')
                expect(page.locator('app-lane-tabs small')).to_have_count(0)
                assert pending
                pending.pop().fulfill(json=solo)
                expect(page.get_by_role('status')).to_contain_text('picks available')
                page.unroute('**/data/**/*.json')
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=team if '/teamplay/' in route.request.url else solo))
                for width, height in [(320, 568), (390, 844), (844, 390), (1366, 768), (1920, 1080)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    for path in ('/', '/results/?mode=solo&' + QUERY, '/results/?mode=teamplay&' + QUERY):
                        page.goto(base + path)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path)
                        skip = page.get_by_role('button', name='Skip to main content')
                        skip.focus(); skip.press('Enter')
                        expect(page.locator('main')).to_be_focused()
                        assert page.evaluate("document.querySelector('main').getBoundingClientRect().top >= document.querySelector('.topbar').getBoundingClientRect().bottom - 1")
                    if width == 390:
                        page.screenshot(path='/tmp/ui-polish-mobile.png')
                        page.add_style_tag(content='html { font-size: 200% !important; }')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        skip.focus(); skip.press('Enter')
                        expect(page.locator('main')).to_be_focused()
                        assert page.evaluate("document.querySelector('main').getBoundingClientRect().top >= document.querySelector('.topbar').getBoundingClientRect().bottom - 1")
                        page.screenshot(path='/tmp/ui-polish-200-root.png')
                page.close()
                page = browser.new_page(viewport={'width': 390, 'height': 844})
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=team if '/teamplay/' in route.request.url else solo))
                page.goto(base + '/results/?mode=solo&' + QUERY)
                expect(page.locator('h1')).to_be_focused()
                trigger = page.get_by_role('button', name='Filters', exact=True)
                trigger.click()
                drawer = page.get_by_role('dialog', name='Refine results')
                expect(drawer).to_be_visible()
                expect(drawer.get_by_role('heading', name='Refine results')).to_be_focused()
                drawer.get_by_role('button', name='Close filters').click()
                expect(trigger).to_be_focused()
                browser.close()
        finally:
            if server:
                server.shutdown()


if __name__ == '__main__':
    run()

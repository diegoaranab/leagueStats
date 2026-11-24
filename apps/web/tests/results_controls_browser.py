"""Results filter interactions and reflow against the Pages artifact."""
import functools
import http.server
import os
import re
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright, expect
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]

def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.symlink(ROOT / 'dist/web/browser', Path(tmp) / 'leagueStats', target_is_directory=True)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={'width': 390, 'height': 844})
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=fixture('test')[1 if '/teamplay/' in route.request.url else 0]))
                page.goto(f'http://127.0.0.1:{server.server_port}/leagueStats/results/?mode=solo&region=lan&tier=gold&window=14d&lane=top&sort=win_rate&difficulty=hard')
                expect(page.locator('h1')).to_be_focused()
                trigger = page.get_by_role('button', name='Filters', exact=True)
                drawer = page.locator('mat-drawer')
                trigger.click()
                heading = drawer.get_by_role('heading', name='Refine results')
                expect(heading).to_be_focused()
                assert heading.bounding_box()['y'] >= page.locator('.topbar').bounding_box()['height']
                page.screenshot(path='/tmp/results-controls-open-focus.png')
                expect(drawer.get_by_role('combobox', name='Region')).to_contain_text('Latin America North')
                expect(drawer.get_by_role('combobox', name='Window')).to_contain_text('Last 14 Days')
                with page.expect_response(lambda response: '/data/teamplay/' in response.url):
                    drawer.locator('button.mode-option').filter(has_text='Flex / Clash').click()
                expect(page).to_have_url(re.compile('mode=teamplay'))
                expect(page.locator('.draft')).to_be_visible()
                expect(drawer).to_have_class(re.compile('mat-drawer-opened'))
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
                    expect(drawer).to_have_class(re.compile('mat-drawer-opened'))
                help_button = drawer.get_by_role('button', name='About difficulty')
                help_button.click()
                expect(drawer.get_by_text('Difficulty is relative', exact=False)).to_be_visible()
                page.screenshot(path='/tmp/results-controls-help.png')
                help_button.focus()
                page.keyboard.press('Enter')
                expect(help_button).to_have_attribute('aria-expanded', 'false')
                page.keyboard.press('Enter')
                expect(drawer.get_by_text('Difficulty is relative', exact=False)).to_be_visible()
                drawer.get_by_role('button', name='Close filters').click()
                expect(trigger).to_be_focused()
                expect(drawer).to_be_hidden()
                assert trigger.bounding_box()['y'] >= page.locator('.topbar').bounding_box()['height']
                page.screenshot(path='/tmp/results-controls-closed-focus.png')
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
                for width, height in [(320,568),(361,640),(390,844),(430,932),(701,800),(768,1024),(844,390),(1080,768),(1081,768),(1366,768),(1920,1080)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
                page.set_viewport_size({'width': 390, 'height': 844})
                page.evaluate("document.documentElement.style.fontSize = '200%'")
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path='/tmp/results-controls-200-text.png')
                trigger.click()
                expect(heading).to_be_focused()
                assert heading.bounding_box()['y'] >= page.locator('.topbar').bounding_box()['height']
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path='/tmp/results-controls-200-drawer.png')
                value = drawer.get_by_role('combobox', name='Region').locator('.mat-mdc-select-value-text')
                assert value.evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                assert value.evaluate('(el) => el.scrollHeight <= el.clientHeight + 1')
                drawer.get_by_role('button', name='Close filters').click()
                expect(trigger).to_be_focused()
                expect(drawer).not_to_have_class(re.compile('mat-drawer-opened'))
                expect(drawer).to_be_hidden()
                page.evaluate("document.documentElement.style.fontSize = ''")
                page.set_viewport_size({'width': 1366, 'height': 768})
                page.screenshot(path='/tmp/results-controls-desktop.png')
                for label in ('Region', 'Window'):
                    control = page.locator('.results-shell__content app-filter-bar').get_by_role('combobox', name=label)
                    assert control.locator('.mat-mdc-select-value-text').evaluate('(el) => el.scrollWidth <= el.clientWidth + 1')
                page.set_viewport_size({'width': 390, 'height': 844})
                trigger.click()
                expect(heading).to_be_focused()
                page.set_viewport_size({'width': 1366, 'height': 768})
                expect(drawer).not_to_have_class(re.compile('mat-drawer-opened'))
                expect(page.locator('h1')).to_be_focused()
                browser.close()
        finally:
            server.shutdown()

if __name__ == '__main__':
    run()

"""Smoke the built Pages artifact using a static server with no SPA fallback.

Run after the Pages-base build and create-route-entries.mjs, with Playwright installed:
PYTHONPATH=tools/scraper/src python apps/web/tests/results_pages_browser.py
"""
import functools
import http.server
import json
import os
import re
from pathlib import Path
import tempfile
import threading
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright, expect
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]


def run():
    with tempfile.TemporaryDirectory() as tmp:
        os.symlink(ROOT / 'dist/web/browser', Path(tmp) / 'leagueStats', target_is_directory=True)
        delay_dataset = threading.Event()
        dataset_requested = threading.Event()
        release_dataset = threading.Event()

        class Handler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if '/data/' in self.path and self.path.endswith('.json'):
                    if delay_dataset.is_set():
                        dataset_requested.set()
                        release_dataset.wait(timeout=15)
                    data = fixture('scroll')[1 if '/teamplay/' in self.path else 0]
                    # Enough cards to make the saved position impossible in the loading view.
                    data['data']['top'] *= 8
                    body = json.dumps(data).encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                super().do_GET()

        handler = functools.partial(Handler, directory=tmp)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/leagueStats'
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={'width': 1366, 'height': 768})
                page.route('**/data/**/*.json', lambda route: route.fulfill(json=fixture('test')[1 if '/teamplay/' in route.request.url else 0]))
                response = page.goto(base + '/results?mode=teamplay&region=lan&tier=gold_plus&window=14d&lane=middle&sort=win_rate&difficulty=hard')
                assert response.status == 200
                expect(page.locator('h1')).to_have_text('Mid picks')
                assert urlparse(response.url).path == '/leagueStats/results/'
                assert parse_qs(urlparse(response.url).query)['difficulty'] == ['hard']
                assert parse_qs(urlparse(page.url).query)['tier'] == ['gold']
                expect(page.locator('app-filter-bar:visible').get_by_role('combobox', name='Difficulty')).to_contain_text('Hard')
                page.reload()
                expect(page.locator('h1')).to_have_text('Mid picks')
                difficulty = page.locator('app-filter-bar:visible').get_by_role('combobox', name='Difficulty')
                expect(difficulty).to_contain_text('Hard')
                difficulty.click()
                page.get_by_role('option', name='Easy', exact=True).click()
                expect(page).to_have_url(re.compile(r'difficulty=easy'))
                page.get_by_role('link', name='Change setup').click()
                expect(page.get_by_role('combobox', name='Region')).to_contain_text('Latin America North')
                expect(page.get_by_role('combobox', name='Rank')).to_contain_text('Gold')
                expect(page.get_by_role('combobox', name='Window')).to_contain_text('Last 14 Days')
                page.get_by_role('button', name='View recommendations').click()
                expect(page.locator('h1')).to_have_text('Mid picks')
                assert page.evaluate('document.activeElement.tagName') == 'H1'
                query = parse_qs(urlparse(page.url).query)
                assert query == {'mode': ['teamplay'], 'region': ['lan'], 'tier': ['gold'], 'window': ['14d'], 'lane': ['middle'], 'sort': ['win_rate'], 'difficulty': ['easy']}, query
                page.go_back()
                expect(page.get_by_role('combobox', name='Rank')).to_contain_text('Gold')
                page.go_forward()
                expect(page.locator('app-filter-bar:visible').get_by_role('combobox', name='Difficulty')).to_contain_text('Easy')
                page.goto(base + '/results/?mode=invalid&region=invalid&tier=__proto__&window=invalid&lane=invalid&sort=invalid&difficulty=invalid')
                expect(page.locator('h1')).to_have_text('Top picks')
                expect(page.locator('app-filter-bar:visible').get_by_role('combobox', name='Rank')).to_contain_text('Diamond')
                expect(page.locator('app-filter-bar:visible').get_by_role('combobox', name='Difficulty')).to_contain_text('All levels')
                page.goto(base + '/')
                expect(page.get_by_role('combobox', name='Rank')).to_contain_text('Diamond')
                expect(page.get_by_role('combobox', name='Region')).to_contain_text('North America')
                page.get_by_role('button', name='View recommendations').click()
                expect(page.locator('h1')).to_have_text('Top picks')
                assert parse_qs(urlparse(page.url).query)['difficulty'] == ['all']
                page.unroute('**/data/**/*.json')
                for mode in ('solo', 'teamplay'):
                    delay_dataset.clear()
                    dataset_requested.clear()
                    release_dataset.clear()
                    page.goto(base + f'/results/?mode={mode}&region=na&tier=gold&window=7d&lane=top&difficulty=all')
                    expect(page.locator('app-champion-card')).to_have_count(40)
                    page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight * 0.7)')
                    saved_y = page.evaluate('window.scrollY')
                    assert saved_y > 1000, saved_y
                    # Activate the link without Playwright scrolling it into view first.
                    page.get_by_role('link', name='Change setup').dispatch_event('click')
                    expect(page.get_by_role('button', name='View recommendations')).to_be_visible()
                    delay_dataset.set()
                    page.go_back(wait_until='commit')
                    assert dataset_requested.wait(timeout=10), 'Returning dataset was not requested'
                    page.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                    assert page.evaluate('document.documentElement.scrollHeight - innerHeight') < saved_y
                    release_dataset.set()
                    expect(page.locator('app-champion-card')).to_have_count(40)
                    page.wait_for_function('(y) => Math.abs(window.scrollY - y) < 20', arg=saved_y)

                # Query-param navigation reuses ResultsPageComponent. A popstate
                # back to this region starts a fresh dataset request while the
                # router's normal scroll event runs against the short loading view.
                page.goto(base + '/results/?mode=solo&region=na&tier=gold&window=7d&lane=top')
                expect(page.locator('app-champion-card')).to_have_count(40)
                page.evaluate("window.__resultsShell = document.querySelector('.results-shell')")
                region = page.locator('app-filter-bar:visible').get_by_role('combobox', name='Region')
                region.click()
                page.get_by_role('option', name='Latin America North').click()
                expect(page).to_have_url(re.compile(r'region=lan'))
                expect(page.locator('app-champion-card')).to_have_count(40)
                assert page.evaluate("window.__resultsShell === document.querySelector('.results-shell')")
                assert urlparse(page.url).path.rstrip('/') == '/leagueStats/results'
                page.evaluate('window.scrollTo(0, document.documentElement.scrollHeight * 0.7)')
                saved_y = page.evaluate('window.scrollY')
                assert saved_y > 1000, saved_y

                page.go_back(wait_until='commit')
                expect(page).to_have_url(re.compile(r'region=na'))
                expect(page.locator('app-champion-card')).to_have_count(40)
                assert page.evaluate("window.__resultsShell === document.querySelector('.results-shell')")

                delay_dataset.set()
                dataset_requested.clear()
                release_dataset.clear()
                page.go_forward(wait_until='commit')
                assert dataset_requested.wait(timeout=10), 'Forward dataset was not withheld'
                expect(page).to_have_url(re.compile(r'region=lan'))
                page.evaluate('new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                assert page.evaluate('document.documentElement.scrollHeight - innerHeight') < saved_y
                assert page.evaluate("window.__resultsShell === document.querySelector('.results-shell')")
                release_dataset.set()
                expect(page.locator('app-champion-card')).to_have_count(40)
                page.wait_for_function('(y) => Math.abs(window.scrollY - y) < 20', arg=saved_y)
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    run()

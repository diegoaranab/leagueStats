"""Deterministic Results data-state checks against a Pages artifact or explicit URL."""
import asyncio
import copy
import functools
import http.server
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright
from playwright.async_api import async_playwright, expect as async_expect
from teamplay_bans_browser import fixture

ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = os.environ.get('RESULTS_DATA_STATES_TEST_URL', '').strip()
QUERY = '?mode=solo&region=lan&tier=gold&window=14d&lane=top&sort=win_rate&difficulty=hard'


def run():
    server = None
    if EXTERNAL:
        parsed = urlparse(EXTERNAL)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('RESULTS_DATA_STATES_TEST_URL must be an absolute HTTP(S) URL')
        base = EXTERNAL.rstrip('/')
    else:
        tmp = tempfile.TemporaryDirectory()
        os.symlink(ROOT / 'dist/web/browser', Path(tmp.name) / 'leagueStats', target_is_directory=True)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp.name))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}/leagueStats'
    print(f'Results data states browser target: {base}')
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script('''() => {
                window.spinnerSeen = false;
                new MutationObserver(() => {
                    if (document.querySelector('[role="progressbar"][aria-label="Loading recommendations"]')) window.spinnerSeen = true;
                }).observe(document, { childList: true, subtree: true });
            }''')
            solo, team = fixture('states')
            solo['meta'].update(source='fixture', generated_at_utc='2026-01-01T00:00:00Z')
            state = {'payload': solo, 'status': 200, 'abort': False, 'malformed': False}
            def response(route):
                if state['abort']:
                    route.abort('failed')
                elif state['malformed']:
                    route.fulfill(status=200, content_type='application/json', body='<html>invalid</html>')
                else:
                    route.fulfill(status=state['status'], json=state['payload'])
            page.route('**/data/**/*.json', response)
            page.goto(base + '/results/' + QUERY)
            expect(page.get_by_role('status')).to_have_text('Dataset ready')
            assert not page.evaluate('window.spinnerSeen'), 'Fast load flashed a spinner'
            page.get_by_text('Data details', exact=True).click()
            expect(page.get_by_text('Source: fixture')).to_be_visible()
            page.screenshot(path='/tmp/results-data-healthy-details.png')
            page.get_by_text('Data details', exact=True).click()
            for width, height in [(320, 568), (390, 844), (1366, 768), (1920, 1080)]:
                page.set_viewport_size({'width': width, 'height': height})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=f'/tmp/results-data-healthy-solo-{width}.png')
            page.set_viewport_size({'width': 390, 'height': 844})
            page.add_style_tag(content='html { font-size: 200% !important; }')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path='/tmp/results-data-200-root-text.png')
            page.reload()

            state['payload'] = team
            page.goto(base + '/results/' + QUERY.replace('mode=solo', 'mode=teamplay'))
            expect(page.locator('.picks-list li').first).to_be_visible()
            page.screenshot(path='/tmp/results-data-healthy-teamplay.png')
            limited = copy.deepcopy(team)
            limited['meta'].update(is_partial=True, oracle_source='cache', warnings=[
                "Oracle competitive slice only had 1 patch values available; requested 2.",
                "Oracle competitive slice includes rows where datacompleteness != 'complete'.",
                'Informational fixture warning',
            ])
            state['payload'] = limited
            page.goto(base + '/results/' + QUERY.replace('mode=solo', 'mode=teamplay'))
            expect(page.get_by_role('status')).to_have_text('Limited data coverage')
            expect(page.get_by_text('Professional coverage is limited.', exact=False)).to_be_visible()
            expect(page.get_by_text('Cached professional source')).to_be_visible()
            expect(page.locator('.picks-list li').first).to_be_visible()
            page.screenshot(path='/tmp/results-data-limited-teamplay.png')
            page.get_by_text('Data details', exact=True).click()
            expect(page.get_by_text('Informational fixture warning')).to_be_visible()
            page.screenshot(path='/tmp/results-data-limited-details.png')

            empty = copy.deepcopy(solo)
            empty['data']['top'] = []
            state['payload'] = empty
            page.goto(base + '/results/' + QUERY)
            expect(page.get_by_text('There are no picks in this lane.')).to_be_visible()

            no_optional = copy.deepcopy(solo)
            no_optional['meta'] = {}
            state['payload'] = no_optional
            page.reload()
            expect(page.get_by_role('status')).to_have_text('Dataset loaded; see data details')
            expect(page.locator('.picks-list li').first).to_be_visible()

            filtered = copy.deepcopy(solo)
            for champion in filtered['data']['top']:
                champion['difficulty'] = 'easy'
            state['payload'] = filtered
            page.reload()
            expect(page.get_by_text('No picks match Hard difficulty.')).to_be_visible()
            expect(page.get_by_text('Bans cover the whole lane and are not limited by difficulty.')).to_be_visible()
            page.screenshot(path='/tmp/results-data-filtered.png')
            page.get_by_role('button', name='Clear difficulty').focus()
            page.keyboard.press('Enter')
            expect(page.get_by_text('No picks match Hard difficulty.')).to_have_count(0)
            expect(page.locator('#picks-heading')).to_be_focused()
            params = parse_qs(urlparse(page.url).query)
            assert params == dict(mode=['solo'], region=['lan'], tier=['gold'], window=['14d'], lane=['top'], sort=['win_rate'], difficulty=['all'])

            missing = copy.deepcopy(solo)
            del missing['data']['top']
            state['payload'] = missing
            page.goto(base + '/results/' + QUERY)
            expect(page.get_by_text('Data for this lane is unavailable.', exact=False)).to_be_visible()
            assert parse_qs(urlparse(page.url).query)['lane'] == ['top']
            page.screenshot(path='/tmp/results-data-lane-unavailable.png')
            page.get_by_role('radio', name='Jungle', exact=False).click()
            assert parse_qs(urlparse(page.url).query)['lane'] == ['jungle']

            missing_team = copy.deepcopy(team)
            del missing_team['data']['top']
            state['payload'] = missing_team
            page.goto(base + '/results/' + QUERY.replace('mode=solo', 'mode=teamplay'))
            expect(page.get_by_text('Data for this lane is unavailable.', exact=False)).to_be_visible()
            expect(page.get_by_text('Lineup unavailable because lane data is missing.')).to_be_visible()
            expect(page.get_by_text('No standout bans for this selection.')).to_have_count(0)

            state['status'] = 404
            page.goto(base + '/results/' + QUERY)
            expect(page.get_by_role('status')).to_contain_text('unavailable')
            page.screenshot(path='/tmp/results-data-dataset-unavailable.png')
            state['status'] = 410
            page.reload()
            expect(page.get_by_role('status')).to_contain_text('unavailable')
            state['status'] = 500
            page.reload()
            expect(page.get_by_role('button', name='Retry')).to_be_visible()
            page.screenshot(path='/tmp/results-data-failure.png')
            page.get_by_role('button', name='Retry').click()
            expect(page.get_by_role('button', name='Retry')).to_be_visible()
            state['abort'] = True
            page.get_by_role('button', name='Retry').click()
            expect(page.get_by_role('button', name='Retry')).to_be_visible()
            state['abort'] = False
            state['malformed'] = True
            page.get_by_role('button', name='Retry').click()
            expect(page.get_by_role('button', name='Retry')).to_be_visible()
            state['malformed'] = False
            state['status'], state['payload'] = 200, {'unexpected': True}
            page.get_by_role('button', name='Retry').click()
            expect(page.get_by_role('button', name='Retry')).to_be_visible()
            state['status'], state['payload'] = 200, solo
            page.get_by_role('button', name='Retry').click()
            expect(page.get_by_role('status')).to_have_text('Dataset ready')
            expect(page.locator('#picks-heading')).to_be_focused()
            page.screenshot(path='/tmp/results-data-recovered.png')
            assert not errors, errors
            browser.close()
        asyncio.run(check_loading_and_races(base))
    finally:
        if server:
            server.shutdown()
            server.server_close()
            tmp.cleanup()


async def check_loading_and_races(base):
    solo, _ = fixture('race')
    solo['meta'].update(source='fixture', generated_at_utc='2026-01-01T00:00:00Z')
    requests = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={'width': 1366, 'height': 768})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))

        async def response(route):
            requests.append(route.request.url)
            number = len(requests)
            if number <= 2 or number == 4:
                await asyncio.sleep(1)
            payload = copy.deepcopy(solo)
            for champion in payload['data']['top']:
                champion['name'] += f' request{number}'
            try:
                if number == 1:
                    await route.fulfill(status=500, body='delayed failure')
                else:
                    await route.fulfill(json=payload)
            except Exception as error:
                # Only canceled obsolete requests may reject fulfillment.
                if number == 3:
                    errors.append(str(error))

        await page.route('**/data/**/*.json', response)
        await page.goto(base + '/results/' + QUERY, wait_until='domcontentloaded')
        await async_expect(page.get_by_role('status')).to_have_text('Loading recommendations')
        await async_expect(page.get_by_role('progressbar', name='Loading recommendations')).to_be_visible()
        await page.screenshot(path='/tmp/results-data-loading.png')
        region = page.get_by_role('combobox', name='Region')
        await region.click()
        await page.get_by_role('option', name='North America', exact=True).click()
        await region.click()
        await page.get_by_role('option', name='Latin America North', exact=True).click()
        await async_expect(page.get_by_text('Ahritoprace request3')).to_be_visible()
        await asyncio.sleep(1.1)
        await async_expect(page.get_by_text('Ahritoprace request3')).to_be_visible()
        assert len(requests) == 3, requests
        # Refinements do not start another dataset request.
        await page.get_by_role('radio', name='Jungle', exact=False).click()
        await page.get_by_role('radio', name='Top', exact=False).click()
        sort = page.get_by_role('combobox', name='Sort by')
        await sort.click()
        await page.get_by_role('option', name='Pick rate', exact=True).click()
        difficulty = page.get_by_role('combobox', name='Difficulty')
        await difficulty.click()
        await page.get_by_role('option', name='Easy', exact=True).click()
        assert len(requests) == 3, requests
        await region.click()
        await page.get_by_role('option', name='North America', exact=True).click()
        await async_expect(page.get_by_role('status')).to_have_text('Loading recommendations')
        await page.get_by_role('link', name='Change setup').click()
        await asyncio.sleep(1.1)
        await async_expect(page.get_by_role('heading', name='Top picks')).to_have_count(0)
        assert not errors, errors

        # Retry stays in the current URL and must not steal later focus.
        retry_page = await browser.new_page(viewport={'width': 1366, 'height': 768})
        retry_count = 0
        async def retry_response(route):
            nonlocal retry_count
            retry_count += 1
            if retry_count == 1:
                await route.fulfill(status=500, body='fixture failure')
            else:
                await asyncio.sleep(.5)
                await route.fulfill(json=solo)
        await retry_page.route('**/data/**/*.json', retry_response)
        await retry_page.goto(base + '/results/' + QUERY)
        retry = retry_page.get_by_role('button', name='Retry')
        await async_expect(retry).to_be_visible()
        original_url = retry_page.url
        await retry.focus()
        await retry_page.keyboard.press('Enter')
        setup = retry_page.get_by_role('link', name='Change setup')
        await setup.focus()
        await async_expect(retry_page.get_by_role('status')).to_have_text('Dataset ready')
        await async_expect(setup).to_be_focused()
        assert retry_page.url == original_url and retry_count == 2
        await browser.close()


if __name__ == '__main__':
    run()

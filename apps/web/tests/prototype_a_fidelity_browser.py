"""Check Prototype A geometry and behavior against the built Pages app.

Build with --base-href /leagueStats/ and create the static route entries first.
PROTOTYPE_A_TEST_URL opts into an absolute external Pages URL; datasets and
portraits are still intercepted with the original historical fixture.
Pass --evidence DIR to write viewport captures, original references and metrics.
"""
import argparse
from contextlib import contextmanager
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect, sync_playwright

WEB = Path(__file__).resolve().parents[1]
REFERENCE = WEB.parents[1] / 'docs/references/prototype-a'
ORIGINAL_METRICS = json.loads((REFERENCE / 'research/render-metrics.json').read_text())
CONTEXT = 'region=na&tier=diamond&window=7d&lane=top&sort=tier&difficulty=all'
MODES = {'solo': 'solo', 'team': 'teamplay'}
VIEWPORTS = ((1366, 768), (1920, 1080), (390, 844), (320, 568), (844, 390))


@contextmanager
def pages_target():
    external = os.environ.get('PROTOTYPE_A_TEST_URL', '').strip()
    if external:
        parsed = urlparse(external)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('PROTOTYPE_A_TEST_URL must be an absolute HTTP(S) URL')
        yield external.rstrip('/')
        return
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, 'leagueStats').symlink_to(WEB / 'dist/web/browser', target_is_directory=True)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp)
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                yield f'http://127.0.0.1:{server.server_port}/leagueStats'
            finally:
                server.shutdown()
                thread.join()


def settle(page):
    page.evaluate("""async () => {
      await document.fonts.ready;
      const images = [...document.images].filter(image => {
        const box = image.getBoundingClientRect();
        return box.width && box.top < innerHeight && box.bottom > 0;
      });
      await Promise.all(images.map(image => image.decode()));
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (!document.fonts.check('700 16px "Space Grotesk"') ||
          ![...document.fonts].some(font => font.family === 'Space Grotesk' && font.status === 'loaded')) {
        throw new Error('Space Grotesk did not load');
      }
    }""")


def attach_fixtures(page):
    datasets = {
        'solo': json.loads((REFERENCE / 'assets/solo-source.json').read_text()),
        'team': json.loads((REFERENCE / 'assets/team-source.json').read_text()),
    }
    page.route('**/data/**/*.json', lambda route: route.fulfill(
        json=datasets['team' if '/teamplay/' in urlparse(route.request.url).path else 'solo']))
    page.route('https://cdn5.lolalytics.com/champx46/*', lambda route: route.fulfill(
        path=str(REFERENCE / 'assets' / Path(urlparse(route.request.url).path).name)))
    return datasets


def visit(page, base, screen):
    path = '/' if screen == 'home' else f'/results/?mode={MODES[screen]}&{CONTEXT}'
    assert page.goto(base + path).status == 200
    if screen == 'home':
        expect(page.get_by_role('heading', name='Know who to lock in.')).to_be_visible()
    else:
        expect(page.locator('app-champion-card')).to_have_count(24 if screen == 'solo' else 9)
    settle(page)


def metrics(page):
    return page.evaluate("""() => {
      const box = element => {
        if (!element || !element.getClientRects().length) return null;
        const r = element.getBoundingClientRect();
        return {x: Math.round(r.x), y: Math.round(r.top + scrollY), w: Math.round(r.width),
                h: Math.round(r.height), end: Math.round(r.bottom + scrollY)};
      };
      const selectors = {
        toolbar: '.topbar-inner', title: 'h1', form: '.setup', sample: '.home-sample',
        homeCta: '.cta-button', roles: '.lane-group', picks: '.picks',
        rankingFilters: '.ranking-filters', canonical: '.champion-card--canonical',
        firstAlternative: '.picks-list li:nth-child(2)', bans: '.recommended-bans',
        lineup: '.easy-lineup', draftEntry: '.quick-jumps button', draft: '.draft'
      };
      const clipped = [...document.querySelectorAll(
        'h1,h2,h3,p,strong,small,.field .mat-mdc-select-value-text,.stat dt,.stat dd,button'
      )].filter(el => el.clientWidth && getComputedStyle(el).visibility === 'visible' &&
          !el.closest('.visually-hidden') && el.scrollWidth > el.clientWidth + 3)
        .map(el => el.textContent.trim());
      return {
        viewport: [innerWidth, innerHeight], doc: [document.documentElement.scrollWidth,
          document.documentElement.scrollHeight], scrollY, clipped,
        fonts: [...document.fonts].filter(font => font.status === 'loaded')
          .map(font => font.family + ' ' + font.weight),
        ...Object.fromEntries(Object.entries(selectors)
          .map(([name, selector]) => [name, box(document.querySelector(selector))])),
        alternativesFullyVisible: [...document.querySelectorAll('.champion-card:not(.champion-card--canonical)')]
          .filter(el => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }).length
      };
    }""")


def record(page, name, evidence, measurements, reference=None):
    settle(page)
    data = metrics(page)
    assert data['viewport'][0] == data['doc'][0], (name, data)
    assert not data['clipped'], (name, data['clipped'])
    original = f'a-{name}' if reference is None else reference
    measurements[name] = {
        'reference': ORIGINAL_METRICS.get(original),
        'candidate': data,
        'referenceScreenshot': f'{original}.png' if (REFERENCE / 'images' / f'{original}.png').exists() else None,
    }
    if evidence:
        page.screenshot(path=evidence / 'candidate' / f'{name}.png', animations='disabled')
        original_file = REFERENCE / 'images' / f'{original}.png'
        if original_file.exists():
            shutil.copyfile(original_file, evidence / 'reference' / original_file.name)
    return data


def match_reference_scroll(page, name):
    page.evaluate('y => window.scrollTo(0, y)', ORIGINAL_METRICS[f'a-{name}']['scrollY'])


def assert_default_geometry(name, data):
    original = ORIGINAL_METRICS[f'a-{name}']
    for field in ('homeCta', 'canonical', 'bans', 'lineup', 'draftEntry'):
        before, after = original[field], data[field]
        if before and after:
            assert abs(before['y'] - after['y']) <= 8, (name, field, before, after)
    assert data['alternativesFullyVisible'] == original['alternativesFullyVisible'], name


def assert_rail(page, mode, height):
    rail = page.locator('.solo-bans' if mode == 'solo' else '.draft')
    first = page.locator('.picks-list li').first.bounding_box()
    box = rail.bounding_box()
    bans = rail.locator('.ban-item').first.bounding_box()
    assert first['x'] + first['width'] < box['x'], (mode, first, box)
    assert 0 <= box['y'] <= first['y'] and first['y'] < height, (mode, first, box)
    assert bans['y'] >= 0 and bans['y'] + bans['height'] <= height, (mode, bans)


def exercise_jump(page, name, destination):
    entry = page.get_by_role('button', name=name, exact=True)
    expect(entry).to_be_in_viewport()
    entry.focus()
    page.keyboard.press('Enter')
    expect(page.locator(destination)).to_be_focused()
    expect(page.locator(destination)).to_be_in_viewport()
    expect(page.get_by_role('button', name='Return to Picks')).to_be_visible()


def return_to_picks(page, url):
    back = page.get_by_role('button', name='Return to Picks')
    back.focus()
    page.keyboard.press('Enter')
    expect(page.locator('#picks-heading')).to_be_focused()
    expect(page.locator('#picks-heading')).to_be_in_viewport()
    assert page.url == url


def check_viewports(browser, base, evidence, measurements, errors):
    for width, height in VIEWPORTS:
        landscape = (width, height) == (844, 390)
        context = browser.new_context(viewport={'width': width, 'height': height},
                                      is_mobile=width < 500, has_touch=width < 500 or landscape,
                                      reduced_motion='reduce' if landscape else 'no-preference',
                                      device_scale_factor=1)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        attach_fixtures(page)
        for screen in ('home', 'solo', 'team'):
            visit(page, base, screen)
            size = f'{width}x{height}'
            prefix = 'landscape-' if landscape else ''
            name = f'{prefix}{screen}-{size}'
            data = record(page, name, evidence, measurements)
            assert_default_geometry(name, data)
            if screen == 'home':
                assert (data['sample']['x'] < data['form']['x']) if width > 864 else (
                    data['title']['end'] < data['form']['y'] < data['sample']['y'])
                if not landscape:
                    assert data['homeCta']['end'] <= height
                if width == 390:
                    page.get_by_role('button', name='Flex / Clash', exact=False).press('Space')
                    submit = page.get_by_role('button', name='View recommendations')
                    submit.focus()
                    record(page, f'keyboard-home-{size}', evidence, measurements)
                    submit.press('Enter')
                    expect(page.get_by_role('heading', name='Flex / Clash', exact=True)).to_be_focused()
            elif width > 864:
                assert_rail(page, screen, height)
            else:
                assert data['roles']['end'] - 12 <= data['draftEntry']['y'] < data['picks']['y']
            if screen == 'solo' and width == 390:
                url = page.url
                exercise_jump(page, 'Recommended bans', '#recommended-bans-heading')
                record(page, f'solo-bans-keyboard-{size}', evidence, measurements)
                match_reference_scroll(page, f'solo-bans-{size}')
                record(page, f'solo-bans-{size}', evidence, measurements)
                return_to_picks(page, url)
                detail = page.get_by_role('button', name='More details about Darius')
                detail.focus()
                page.keyboard.press('Enter')
                expect(detail).to_have_attribute('aria-expanded', 'true')
                record(page, f'solo-details-{size}', evidence, measurements)
                page.keyboard.press('Space')
                expect(detail).to_have_attribute('aria-expanded', 'false')
            if screen == 'team' and width in (390, 1366):
                url = page.url
                if width == 390:
                    exercise_jump(page, 'Draft tools (bans & lineup)', '#draft-heading')
                    record(page, f'draft-keyboard-{size}', evidence, measurements)
                    match_reference_scroll(page, f'draft-{size}')
                record(page, f'draft-{size}', evidence, measurements)
                page.get_by_role('button', name='Build lineup').click()
                expect(page.locator('.role-card')).to_have_count(5)
                match_reference_scroll(page, f'lineup-{size}')
                record(page, f'lineup-{size}', evidence, measurements)
                if width == 390:
                    page.get_by_role('button', name='Hide lineup').click()
                    return_to_picks(page, url)
                    page.get_by_role('combobox', name='Sort by').click()
                    page.get_by_role('option', name='Pick rate', exact=True).click()
                    page.evaluate('window.scrollTo(0, 0)')
                    expect(page.locator('.picks-list h3').first).to_have_text('Renekton')
                    expect(page.locator('#canonical-pick h3')).to_have_text('Camille')
                    record(page, f'pick-rate-team-{size}', evidence, measurements)
                    page.get_by_role('button', name='Jump to recommended pick', exact=False).click()
                    expect(page.locator('#canonical-pick')).to_be_focused()
                    page.get_by_role('link', name='Solo', exact=True).click()
                    expect(page.locator('.toolbar-nav [aria-current="page"]')).to_have_text('Solo')
                    assert parse_qs(urlparse(page.url).query) == {
                        'mode': ['solo'], 'region': ['na'], 'tier': ['diamond'], 'window': ['7d'],
                        'lane': ['top'], 'sort': ['tier'], 'difficulty': ['all'],
                    }
        context.close()
        print(f'PASS prototype composition and applicable interactions at {width}×{height}')


def check_long_and_text(browser, base, evidence, measurements):
    page = browser.new_page(viewport={'width': 1366, 'height': 768}, reduced_motion='reduce')
    data = attach_fixtures(page)
    original_top = data['solo']['data']['top']
    long_top = original_top + [
        {**champion, 'name': f"{champion['name']} example", 'filtered_rank': 25 + i}
        for i, champion in enumerate(original_top[:14])
    ]
    for count in (10, 20, 30, 38):
        data['solo']['data']['top'] = long_top[:count]
        assert page.goto(f'{base}/results/?mode=solo&{CONTEXT}').status == 200
        expect(page.locator('.picks-list li')).to_have_count(count)
        assert_rail(page, 'solo', 768)
    record(page, 'solo-long-list-1366x768', evidence, measurements)
    print('PASS desktop Solo bans alongside the first row with 10, 20, 30 and 38 picks')
    page.close()

    page = browser.new_page(viewport={'width': 390, 'height': 844}, reduced_motion='reduce',
                            is_mobile=True, has_touch=True, device_scale_factor=1)
    attach_fixtures(page)
    for variant in ('text', 'root'):
        for screen in ('home', 'solo', 'team'):
            visit(page, base, screen)
            if screen == 'home':
                page.get_by_role('combobox', name='Region').click()
                page.get_by_role('option', name='Latin America North').click()
            if variant == 'text':
                # Apply the original render script's text-only resize method.
                page.evaluate("""() => {
                  const elements = [...document.querySelectorAll('body *')]
                    .filter(el => el instanceof HTMLElement && getComputedStyle(el).display !== 'none');
                  const sizes = elements.map(el => parseFloat(getComputedStyle(el).fontSize));
                  elements.forEach((el, index) => el.style.fontSize = sizes[index] * 2 + 'px');
                }""")
            else:
                page.evaluate("document.documentElement.style.fontSize = '200%'")
            record(page, f'{variant}-200-{screen}-390x844', evidence, measurements)
            selector = '.setup' if screen == 'home' else '.champion-card--canonical'
            page.locator(selector).evaluate("element => element.scrollIntoView({block:'start'})")
            if variant == 'text' and screen != 'home':
                # The reference anchors the ranked row 12px below the viewport top.
                page.evaluate('window.scrollBy(0, -12)')
            if screen == 'home':
                expect(page.get_by_role('combobox', name='Region')).to_contain_text('Latin America North')
            record(page, f'{variant}-200-{screen}-detail-390x844', evidence, measurements)
    page.close()
    print('PASS 200% text-only and root text, extended region value and reduced motion')


def check_native_zoom(chromium, base, evidence, measurements):
    extension = REFERENCE / 'research/zoom-extension'
    with tempfile.TemporaryDirectory() as profile:
        context = chromium.launch_persistent_context(
            profile, channel='chromium', viewport={'width': 1366, 'height': 768}, device_scale_factor=1,
            args=[f'--disable-extensions-except={extension}', f'--load-extension={extension}'])
        try:
            page = context.pages[0]
            attach_fixtures(page)
            worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
            for screen in ('home', 'solo', 'team'):
                visit(page, base, screen)
                zoom = worker.evaluate("""async url => {
                    const tab = (await chrome.tabs.query({})).find(item => item.url === url);
                    await chrome.tabs.setZoom(tab.id, 2);
                    return chrome.tabs.getZoom(tab.id);
                }""", page.url)
                assert zoom == 2
                page.wait_for_function('innerWidth === 683')
                record(page, f'native-zoom-200-{screen}-1366x768', evidence, measurements)
        finally:
            context.close()
    print('PASS Chromium native page zoom at 200% (683×384 CSS viewport)')


def run(evidence=None, native_zoom=False):
    if evidence:
        for folder in ('reference', 'candidate'):
            (evidence / folder).mkdir(parents=True, exist_ok=True)
    measurements, errors = {}, []
    with pages_target() as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            check_viewports(browser, base, evidence, measurements, errors)
            check_long_and_text(browser, base, evidence, measurements)
        finally:
            browser.close()
        if native_zoom:
            check_native_zoom(pw.chromium, base, evidence, measurements)
    assert not errors, errors
    if evidence:
        (evidence / 'measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
    print('PASS integrated Prototype A regression')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--native-zoom', action='store_true')
    args = parser.parse_args()
    run(args.evidence, args.native_zoom)

"""Fixture browser regression. Run with the scraper's Python/Playwright dependencies.

Start `npm start -- --port 4210` in apps/web, then from the repo root run:
PYTHONPATH=tools/scraper/src python3 apps/web/tests/teamplay_bans_browser.py
No scraping or public dataset writes are performed.
"""
import re
import os
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect
from loltee_scraper.build_teamplay import build_teamplay_dataset
from loltee_scraper.oracle_teamplay import OracleRoleStats, OracleChampionStats, OracleTeamplaySnapshot

LANES = {"top": "Top", "jungle": "Jungle", "middle": "Mid", "bottom": "ADC", "support": "Support"}
BASE = os.environ.get("TEAMPLAY_TEST_URL", "http://127.0.0.1:4210")


def fixture(context):
    data, roles, stats = {}, {}, {}
    for lane in LANES:
        data[lane] = []
        for i, name in enumerate(["Ahri", "Lux", "Annie", "Veigar", "Zed"]):
            name = name + lane + context
            data[lane].append(dict(
                name=name, lane=lane, rank=i + 1, filtered_rank=i + 1, tier="S",
                pbi=[-1000, 0, 10, 100, 100][i], difficulty=["hard", "easy", "medium", "easy", "hard"][i],
                difficulty_order=[3, 1, 2, 1, 3][i], win_rate=50 + i, pick_rate=5 - i,
                icon_url="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' width='42' height='42'><rect width='42' height='42' fill='teal'/></svg>",
            ))
            roles[(name.lower(), lane)] = OracleRoleStats(10, 0.5, 5, 50, 20, 1, [1, 0.8, 0, 0, 0][i])
            stats[name.lower()] = OracleChampionStats(10 if i < 2 else 0, 0, 1, 10)
    solo = dict(meta=dict(warnings=[], failed_lanes=[], is_partial=False), data=data)
    snapshot = OracleTeamplaySnapshot([], [], 20, roles, stats,
                                     dict.fromkeys(LANES, 1), dict.fromkeys(LANES, 1), 1, False, [], 0, 0)
    team = build_teamplay_dataset(solo_dataset=solo, pro_snapshot=snapshot, region="na", tier="gold", window="7d")
    return solo, team


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def serve(route):
            path = urlparse(route.request.url).path
            context = ''.join(path.rsplit('/', 3)[-3:]).replace('.json', '').replace('7d', 'week').replace('14d', 'fortnight')
            solo, team = fixture(context)
            route.fulfill(json=team if '/teamplay/' in path else solo)

        page.route("**/data/**/*.json", serve)

        def expected(mode, lane="top", context="nagoldweek"):
            names = ["Ahri", "Lux", "Annie"] if mode == "teamplay" else ["Veigar", "Zed", "Annie"]
            return [n + lane + context for n in names]

        def strip(names):
            expect(page.locator('.ban-item__name')).to_have_text(names)

        def select(label, option):
            compact = page.viewport_size['width'] <= 1080
            if compact:
                page.get_by_role('button', name=re.compile(r'Filters')).click()
            page.locator('app-filter-bar:visible').get_by_role('combobox', name=label, exact=True).click()
            page.get_by_role('option', name=option, exact=True).click()
            if compact and page.get_by_role('button', name='Close filters').is_visible():
                page.get_by_role('button', name='Close filters').click()

        for width, height in [(390, 844), (430, 932), (768, 1024), (1366, 768)]:
            page.set_viewport_size(dict(width=width, height=height))
            for mode in ["teamplay", "solo"]:
                page.goto(f"{BASE}/results?mode={mode}&region=na&tier=gold&window=7d&lane=top&sort=ban_priority")
                strip(expected(mode))
                expect(page.locator('app-champion-card h3').first).to_have_text(expected(mode)[0])
                select('Sort by', 'Win rate')
                strip(expected(mode))
                select('Difficulty', 'Easy')
                strip(expected(mode))
                expect(page.locator('app-champion-card')).to_have_count(2)
                select('Difficulty', 'All levels')
                select('Sort by', 'Ban priority')
                for lane, label in LANES.items():
                    page.locator('mat-button-toggle').filter(has=page.locator('.lane-label', has_text=label)).click()
                    strip(expected(mode, lane))
                    expect(page.locator('app-champion-card h3').first).to_have_text(expected(mode, lane)[0])
                card = page.locator('app-champion-card').first
                card.locator('summary').click()
                expect(card.locator('.secondary-row div').filter(has_text='Ban priority')).to_contain_text('#1')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, mode, 'overflow')
                assert page.locator('.ban-item').count() == 3
                page.screenshot(path=f"/tmp/teamplay-bans-{mode}-{width}x{height}.png")
            print(f"PASS {width}x{height}: both modes, all lanes, sorts, difficulty, cards, overflow")

        # Context controls load their corresponding full lane datasets.
        page.goto(f"{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority")
        strip(expected('teamplay'))
        select('Region', 'Latin America North')
        strip(expected('teamplay', context='langoldweek'))
        select('Rank', 'Silver')
        strip(expected('teamplay', context='lansilverweek'))
        select('Window', 'Last 14 Days')
        strip(expected('teamplay', context='lansilverfortnight'))
        # Switch modes through the actual mode control, then restore Solo ban sorting.
        page.locator('app-filter-bar:visible app-mode-selector').get_by_role('button', name='Solo Queue', exact=False).click()
        strip(expected('solo', context='lansilverfortnight'))
        select('Sort by', 'Ban priority')
        expect(page.locator('app-champion-card h3').first).to_have_text(expected('solo', context='lansilverfortnight')[0])

        # Small eligible pools and older data without ranks are safe.
        solo, team = fixture('small')
        team['data']['top'] = sorted(team['data']['top'], key=lambda c: c['teamplay_ban_rank'])[:2]
        page.unroute("**/data/**/*.json")
        page.route("**/data/**/*.json", lambda route: route.fulfill(json=team))
        page.goto(f"{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority")
        expect(page.locator('.ban-item')).to_have_count(2)
        for c in team['data']['top']:
            del c['teamplay_ban_rank']
        page.reload()
        expect(page.locator('.recommended-bans__empty')).to_be_visible()
        assert not errors, errors
        print('PASS context changes, mode switching, small/legacy pools; no browser errors')
        browser.close()


if __name__ == '__main__':
    run()

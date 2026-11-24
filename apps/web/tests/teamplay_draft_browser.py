"""Draft workspace behavior and responsive geometry, using the Teamplay fixture."""
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect
from teamplay_bans_browser import BASE, fixture


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        solo, team = fixture('nagoldweek')
        page.route('**/data/**/*.json', lambda route: route.fulfill(json=team if '/teamplay/' in urlparse(route.request.url).path else solo))
        for width, height in [(320, 568), (390, 844), (844, 390), (1366, 768), (1920, 1080)]:
            page.set_viewport_size(dict(width=width, height=height))
            page.goto(f'{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority')
            draft = page.locator('.draft')
            expect(draft).to_have_count(1)
            expect(draft.locator('app-recommended-bans')).to_have_count(1)
            expect(draft.locator('app-easy-clash-lineup')).to_have_count(1)
            assert page.evaluate("document.querySelector('.picks').compareDocumentPosition(document.querySelector('.draft')) & Node.DOCUMENT_POSITION_FOLLOWING")
            url = page.url
            page.screenshot(path=f'/tmp/draft-team-{width}x{height}-picks.png')
            if width < 1200:
                jump = page.get_by_role('button', name='Go to Draft')
                expect(jump).to_be_visible()
                jump.focus()
                page.keyboard.press('Enter')
                expect(page.locator('#draft-heading')).to_be_focused()
                assert page.locator('#draft-heading').bounding_box()['y'] >= page.locator('.topbar').bounding_box()['height']
                assert page.url == url
                page.screenshot(path=f'/tmp/draft-team-{width}x{height}-draft.png')
                page.get_by_role('button', name='Return to Picks').focus()
                page.keyboard.press('Enter')
                expect(page.locator('#picks-heading')).to_be_focused()
                assert page.url == url
                jump.click()
            else:
                picks_box = page.locator('.picks').bounding_box()
                draft_box = draft.bounding_box()
                assert picks_box['x'] + picks_box['width'] <= draft_box['x']
                assert picks_box['width'] > draft_box['width']
                assert draft_box['x'] + draft_box['width'] <= width
            page.get_by_role('button', name='Build an Easy Clash Team').click()
            expect(page.locator('.role-card')).to_have_count(5)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=f'/tmp/draft-team-{width}x{height}-expanded.png')
            page.locator('.role-card').first.scroll_into_view_if_needed()
            page.screenshot(path=f'/tmp/draft-team-{width}x{height}-lineup.png')
            page.goto(f'{BASE}/results?mode=solo&region=na&tier=gold&window=7d&lane=top&sort=ban_priority')
            expect(page.locator('.draft')).to_have_count(0)
            expect(page.get_by_role('button', name='Go to Draft')).to_have_count(0)
            if width in (390, 1366):
                page.screenshot(path=f'/tmp/draft-solo-{width}x{height}.png')
            print(f'PASS {width}x{height}')
        page.set_viewport_size(dict(width=390, height=844))
        page.goto(f'{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority')
        page.evaluate("document.documentElement.style.fontSize = '200%'")
        page.screenshot(path='/tmp/draft-team-390x844-200percent-root-picks.png')
        page.get_by_role('button', name='Go to Draft').click()
        page.screenshot(path='/tmp/draft-team-390x844-200percent-root-draft.png')
        page.get_by_role('button', name='Build an Easy Clash Team').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path='/tmp/draft-team-390x844-200percent-root-expanded.png')
        print('PASS 200% root text')

        # Stress the wide rail with enlarged root text. The card must reflow
        # from its Picks-column width even though the viewport remains wide.
        page.set_viewport_size(dict(width=1200, height=1000))
        page.goto(f'{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority')
        page.evaluate("document.documentElement.style.fontSize = '200%'")
        picks = page.locator('.picks')
        draft = page.locator('.draft')
        expect(draft).to_be_visible()

        def assert_rail_geometry(label):
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'{label}: document overflow'
            picks_box, draft_box = picks.bounding_box(), draft.bounding_box()
            assert picks_box['x'] + picks_box['width'] <= draft_box['x'], (label, picks_box, draft_box)
            assert draft_box['x'] + draft_box['width'] <= 1200, (label, draft_box)
            draft_overflow = draft.locator('*').evaluate_all("elements => elements.filter(element => { const style = getComputedStyle(element); return style.display !== 'none' && style.visibility !== 'hidden' && element.getClientRects().length && !element.matches('.ban-item__priority, .mat-ripple') && element.scrollWidth > element.clientWidth + 1; }).map(element => ({tag: element.tagName, className: element.className, scrollWidth: element.scrollWidth, clientWidth: element.clientWidth, text: element.textContent.trim().slice(0, 80)}))")
            assert not draft_overflow, (label, draft_overflow)
            ban_rank_clearance = draft.locator('.ban-item').evaluate_all("items => items.map(item => { const rank = item.querySelector('.ban-item__priority'); const portrait = item.querySelector('.ban-item__portrait'); const range = document.createRange(); range.selectNodeContents(rank); return {rankTextRight: range.getBoundingClientRect().right, portraitLeft: portrait.getBoundingClientRect().left}; })")
            assert all(item['rankTextRight'] <= item['portraitLeft'] for item in ban_rank_clearance), (label, ban_rank_clearance)
            for card in page.locator('.picks-list app-champion-card').all():
                card_box = card.bounding_box()
                assert card_box['x'] >= picks_box['x'] - 1 and card_box['x'] + card_box['width'] <= picks_box['x'] + picks_box['width'] + 1, (label, card_box, picks_box)
                for content in card.locator('.card-primary, .card-top, .stat-grid, .sort-evidence, .badge-row, .card-details').all():
                    box = content.bounding_box()
                    if box:
                        assert box['x'] >= picks_box['x'] - 1 and box['x'] + box['width'] <= picks_box['x'] + picks_box['width'] + 1, (label, content, box, picks_box)
            # Compact geometry places the stat block after identity in the row.
            first = page.locator('.picks-list app-champion-card').first
            top_box, stats_box = first.locator('.card-top').bounding_box(), first.locator('.stat-grid').bounding_box()
            assert stats_box['y'] >= top_box['y'] + top_box['height'] - 1, (label, top_box, stats_box)

        assert_rail_geometry('1200px at 200% root text')
        picks.screenshot(path='/tmp/draft-team-1200x1000-200percent-picks.png')
        draft.screenshot(path='/tmp/draft-team-1200x1000-200percent-draft.png')
        page.get_by_role('button', name='Build an Easy Clash Team').click()
        expect(page.locator('.role-card')).to_have_count(5)
        assert_rail_geometry('1200px at 200% root text, lineup expanded')
        draft.screenshot(path='/tmp/draft-team-1200x1000-200percent-expanded.png')
        print('PASS 1200px rail stress at 200% root text')

        # With ample available card width, the desktop comparison columns stay
        # side by side, demonstrating that compact reflow is width driven.
        page.set_viewport_size(dict(width=1920, height=1080))
        page.goto(f'{BASE}/results?mode=teamplay&region=na&tier=gold&window=7d&lane=top&sort=ban_priority')
        first = page.locator('.picks-list app-champion-card').first
        top_box, stats_box = first.locator('.card-top').bounding_box(), first.locator('.stat-grid').bounding_box()
        assert stats_box['x'] >= top_box['x'] + top_box['width'] - 1, (top_box, stats_box)
        assert stats_box['y'] < top_box['y'] + top_box['height'], (top_box, stats_box)
        print('PASS wide container retains comparison layout')
        browser.close()


if __name__ == '__main__':
    run()

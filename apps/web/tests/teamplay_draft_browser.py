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
        browser.close()


if __name__ == '__main__':
    run()

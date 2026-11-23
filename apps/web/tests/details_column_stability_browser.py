"""Focused disclosure geometry and responsive regression.

Run with the Angular dev server on port 4210:
PYTHONPATH=tools/scraper/src python3 apps/web/tests/details_column_stability_browser.py
"""
import os

from playwright.sync_api import expect, sync_playwright
from teamplay_bans_browser import fixture

BASE = os.environ.get("DETAILS_TEST_URL", "http://127.0.0.1:4210")
SCREENSHOTS = "/tmp/leagueStats-disclosure"


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
        solo, _ = fixture("details")
        page.route("**/data/**/*.json", lambda route: route.fulfill(json=solo))

        def open_results(width, height):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(f"{BASE}/results?mode=solo&region=na&tier=gold&window=7d&lane=top&sort=win_rate")
            expect(page.locator("app-champion-card")).to_have_count(5)
            return page.locator("app-champion-card").first

        card = open_results(1366, 768)
        trigger = card.get_by_role("button", name="More details")
        selectors = [".rank", ".portrait", ".stat:nth-child(1)", ".stat:nth-child(2)", ".stat:nth-child(3)", ".card-details"]

        def x_positions():
            return [card.locator(selector).evaluate("element => element.getBoundingClientRect().x") for selector in selectors]

        before = x_positions()
        os.makedirs(SCREENSHOTS, exist_ok=True)
        card.screenshot(path=f"{SCREENSHOTS}/1366-closed.png")
        expect(trigger).to_have_attribute("aria-expanded", "false")
        trigger.focus()
        assert page.evaluate("getComputedStyle(document.activeElement).outlineStyle !== 'none'"), "disclosure focus ring is missing"
        page.keyboard.press("Enter")
        expect(trigger).to_have_attribute("aria-expanded", "true")
        expect(card.locator(".details-panel")).to_be_visible()
        after = x_positions()
        card.screenshot(path=f"{SCREENSHOTS}/1366-open.png")
        deltas = [round(after_x - before_x, 2) for before_x, after_x in zip(before, after)]
        assert all(abs(delta) <= 2 for delta in deltas), dict(zip(["rank", "portrait", "metric 1", "metric 2", "metric 3", "details trigger"], deltas))
        page.keyboard.press("Space")
        expect(trigger).to_have_attribute("aria-expanded", "false")
        expect(card.locator(".details-panel")).to_be_hidden()
        print("1366 x-position deltas:", dict(zip(["rank", "portrait", "metric 1", "metric 2", "metric 3", "details trigger"], deltas)))

        for width, height, label in [(390, 844, "390"), (320, 568, "320")]:
            card = open_results(width, height)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{width}px closed overflow"
            expect(card.locator(".rank")).to_be_visible()
            expect(card.locator(".portrait")).to_be_visible()
            expect(card.locator(".stat")).to_have_count(3)
            trigger = card.get_by_role("button", name="More details")
            expect(trigger).to_be_visible()
            if label == "390":
                card.screenshot(path=f"{SCREENSHOTS}/390-closed.png")
            trigger.click()
            expect(card.locator(".details-panel")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{width}px open overflow"
            if label == "390":
                card.screenshot(path=f"{SCREENSHOTS}/390-open.png")
            trigger.click()
            expect(card.locator(".details-panel")).to_be_hidden()
            print(f"PASS {width} mobile: hierarchy, metrics, disclosure, no horizontal overflow")

        browser.close()


if __name__ == "__main__":
    run()

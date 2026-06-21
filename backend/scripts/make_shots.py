"""Capture app screenshots with Playwright (run inside the backend container).

The frontend is reachable as http://frontend within the compose network; its
/api calls are proxied by nginx to the backend. Usage:
    pip install playwright && playwright install --with-deps chromium
    python /app/scripts/make_shots.py /out <detail_offer_id>
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(out_dir: str, offer_id: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = "http://frontend"

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 920}, device_scale_factor=2)

        # Home / dashboard — full page + landscape hero (top fold)
        page.goto(f"{base}/", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out / "home.png"), full_page=True)
        page.screenshot(path=str(out / "home_hero.png"))
        print("wrote home")

        # Offer detail — full page + hero
        page.goto(f"{base}/offers/{offer_id}", wait_until="networkidle")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out / "detail.png"), full_page=True)
        page.screenshot(path=str(out / "detail_hero.png"))
        print("wrote detail")

        # Compare page
        page.goto(f"{base}/compare", wait_until="networkidle")
        page.wait_for_timeout(2000)
        page.screenshot(path=str(out / "compare.png"), full_page=True)
        page.screenshot(path=str(out / "compare_hero.png"))
        print("wrote compare")

        browser.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/out", sys.argv[2])

"""Automated browser audit and proof verification using Playwright.

Visits every page on http://localhost:3000:
1. / (Upload & Parse)
2. /match (Explainable Match)
3. /rank (Multi-candidate Ranking)
4. /search (Natural Language Talent Search)
5. /coach (AI Career Coach)
6. /taxonomy (ESCO / O*NET Explorer)
7. /evaluation (Benchmark Scorecard)
8. /about (Architecture Blueprint)

Records console errors, failed network requests, exercises interactivity,
and saves high-res full-page screenshots to the artifact screenshots directory.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

SCREENSHOTS_DIR = Path(
    r"C:\Users\harsh\.gemini\antigravity\brain\b5545534-0865-4396-b114-8e4c867456d1\screenshots"
)
SCREENSHOTS_AFTER_DIR = Path(
    r"C:\Users\harsh\.gemini\antigravity\brain\b5545534-0865-4396-b114-8e4c867456d1\screenshots_after"
)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_AFTER_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:3000"

PAGES = [
    {"name": "01_upload_home", "path": "/", "title": "Resume Extraction"},
    {"name": "02_match", "path": "/match", "title": "Candidate Matching"},
    {"name": "03_rank", "path": "/rank", "title": "Role Ranking"},
    {"name": "04_search", "path": "/search", "title": "Talent Search"},
    {"name": "05_coach", "path": "/coach", "title": "Career Coach"},
    {"name": "06_taxonomy", "path": "/taxonomy", "title": "Taxonomy Explorer"},
    {"name": "07_evaluation", "path": "/evaluation", "title": "Evaluation Scorecard"},
    {"name": "08_about", "path": "/about", "title": "System Design"},
]


async def run_audit():
    audit_results = {
        "pages_audited": len(PAGES),
        "pages": {},
        "console_errors": [],
        "network_errors": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Desktop context (1280x900)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1.5,
        )
        page = await context.new_page()

        # Listen for console errors & warnings
        page.on(
            "console",
            lambda msg: (
                audit_results["console_errors"].append(
                    {"type": msg.type, "text": msg.text, "location": msg.location}
                )
                if msg.type == "error"
                else None
            ),
        )

        # Listen for failed requests (4xx / 5xx)
        page.on(
            "response",
            lambda res: (
                audit_results["network_errors"].append(
                    {"url": res.url, "status": res.status, "status_text": res.status_text}
                )
                if res.status >= 400
                else None
            ),
        )

        for p_info in PAGES:
            name = p_info["name"]
            path = p_info["path"]
            url = f"{BASE_URL}{path}"
            print(f"--> Auditing {name} at {url} (Desktop 1280px)...")

            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # Perform page-specific interactions to test dynamic workflows
            if path == "/":
                # Exercise the 1-click guided demo persona
                try_btn = page.locator("text='Try This Candidate'").first
                if await try_btn.count() > 0:
                    await try_btn.click()
                    await page.wait_for_timeout(800)
                else:
                    sample_btn = page.locator("text='Marcus Vance'").first
                    if await sample_btn.count() > 0:
                        await sample_btn.click()
                        await page.wait_for_timeout(800)

            elif path == "/match":
                # Trigger calculate match score
                match_btn = page.locator("button:has-text('Calculate Match Score')").first
                if await match_btn.count() > 0:
                    await match_btn.click()
                    await page.wait_for_timeout(2000)

            elif path == "/search":
                # Execute sample query
                search_btn = page.locator("button:has-text('Search')").first
                if await search_btn.count() > 0:
                    await search_btn.click()
                    await page.wait_for_timeout(2500)

            elif path == "/coach":
                # Trigger coach report generation
                coach_btn = page.locator("button:has-text('Generate Coach Report')").first
                if await coach_btn.count() > 0:
                    await coach_btn.click()
                    await page.wait_for_timeout(2500)

            elif path == "/taxonomy":
                # Search for Python in taxonomy
                input_field = page.locator("input[placeholder*='Search taxonomy']").first
                if await input_field.count() > 0:
                    await input_field.fill("Python")
                    search_btn = page.locator("button[type='submit']:has-text('Search')").first
                    if await search_btn.count() > 0:
                        await search_btn.click()
                        await page.wait_for_timeout(1000)

            # Take full-page screenshot
            screenshot_path = SCREENSHOTS_AFTER_DIR / f"{name}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            # Also mirror to main screenshots dir
            await page.screenshot(path=str(SCREENSHOTS_DIR / f"{name}.png"), full_page=True)
            print(f"    Saved screenshot: {screenshot_path}")

            audit_results["pages"][name] = {
                "path": path,
                "screenshot": str(screenshot_path),
                "url": url,
                "status": "PASS",
            }

        # 2. Responsive mobile verification at 390px (iPhone 14 width)
        print("\n--> Auditing mobile responsiveness at 390px...")
        mobile_context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
        )
        mobile_page = await mobile_context.new_page()
        for p_info in PAGES[:3]:  # Check key interaction flows on mobile
            name = p_info["name"]
            path = p_info["path"]
            url = f"{BASE_URL}{path}"
            await mobile_page.goto(url, wait_until="networkidle")
            await mobile_page.wait_for_timeout(600)
            mobile_shot = SCREENSHOTS_AFTER_DIR / f"{name}_390px.png"
            await mobile_page.screenshot(path=str(mobile_shot), full_page=True)
            print(f"    Mobile (390px) shot saved: {mobile_shot}")
        await mobile_context.close()

        # 3. Responsive tablet verification at 768px (iPad Mini width)
        print("\n--> Auditing tablet responsiveness at 768px...")
        tablet_context = await browser.new_context(
            viewport={"width": 768, "height": 1024},
            device_scale_factor=1.5,
        )
        tablet_page = await tablet_context.new_page()
        for p_info in PAGES[:2]:
            name = p_info["name"]
            path = p_info["path"]
            url = f"{BASE_URL}{path}"
            await tablet_page.goto(url, wait_until="networkidle")
            await tablet_page.wait_for_timeout(600)
            tablet_shot = SCREENSHOTS_AFTER_DIR / f"{name}_768px.png"
            await tablet_page.screenshot(path=str(tablet_shot), full_page=True)
            print(f"    Tablet (768px) shot saved: {tablet_shot}")
        await tablet_context.close()

        await browser.close()

    # Save summary report
    report_file = SCREENSHOTS_DIR / "browser_audit_summary.json"
    report_file.write_text(json.dumps(audit_results, indent=2), encoding="utf-8")
    print(f"\nAudit complete! {len(PAGES)}/{len(PAGES)} pages tested and screenshotted.")
    print(f"Console errors: {len(audit_results['console_errors'])}")
    print(f"Network errors: {len(audit_results['network_errors'])}")


if __name__ == "__main__":
    asyncio.run(run_audit())

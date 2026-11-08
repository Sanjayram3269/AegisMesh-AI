"""Capture every console page and check responsive and accessible 3D controls."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def login(page, url, credentials):
    page.goto(url)
    page.locator("#username").fill(credentials["agent"]["username"])
    page.locator("#password").fill(credentials["agent"]["password"])
    page.locator("#loginSubmit").click()
    expect(page.locator("#loginDialog")).not_to_be_visible()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--data-dir", default=".local/flagship-check")
    parser.add_argument("--output", default=".local/console-review")
    args = parser.parse_args()
    credentials = json.loads((Path(args.data_dir) / "credentials.json").read_text())
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--enable-unsafe-swiftshader"])
        context = browser.new_context(
            viewport={"width": 1500, "height": 1050}, reduced_motion="reduce"
        )
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        login(page, args.url, credentials)
        page.wait_for_function(
            "document.querySelector('#agentCanvas').dataset.renderer==='webgl'"
        )
        for size in [(1500, 1050), (1024, 900), (390, 844)]:
            page.set_viewport_size({"width": size[0], "height": size[1]})
            for name in [
                "overview",
                "assistant",
                "approvals",
                "activity",
                "policies",
                "checks",
            ]:
                page.locator('nav [data-view="' + name + '"]').click()
                expect(page.locator("#view-" + name)).to_be_visible()
                page.wait_for_timeout(180)
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), f"{name} overflows at {size[0]}px"
                page.screenshot(
                    path=str(output / f"{name}-{size[0]}.png"), full_page=True
                )
                checks.append(f"{name} at {size[0]}px")
        page.set_viewport_size({"width": 1500, "height": 1050})
        page.keyboard.press("Control+k")
        expect(page.locator("#commandDialog")).to_be_visible()
        page.locator('#commandDialog [data-view="overview"]').click()
        expect(page.locator("#commandDialog")).not_to_be_visible()
        for stage in ["intent", "identity", "policy", "risk", "execution", "audit"]:
            page.locator(f'.stage-button[data-stage="{stage}"]').focus()
            page.keyboard.press("Enter")
            expect(
                page.locator(f'.stage-button[data-stage="{stage}"]')
            ).to_have_attribute("aria-pressed", "true")
        expect(page.locator("#toggleMotion")).to_have_attribute(
            "aria-label", "Resume ambient motion"
        )
        page.locator("#toggleMotion").click()
        expect(page.locator("#toggleMotion")).to_have_attribute(
            "aria-label", "Pause ambient motion"
        )
        page.locator("#toggleMotion").click()
        expect(page.locator("#toggleMotion")).to_have_attribute(
            "aria-label", "Resume ambient motion"
        )
        checks += [
            "command navigation",
            "keyboard selection of all six stages",
            "motion control",
        ]
        context.close()
        fallback = p.chromium.launch(headless=True, args=["--disable-webgl"])
        page = fallback.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda e: errors.append(str(e)))
        login(page, args.url, credentials)
        expect(page.locator("#sceneFallback")).to_be_visible()
        page.locator('.stage-button[data-stage="identity"]').click()
        expect(page.locator("#agentName")).to_have_text("Identity verification")
        checks.append("usable stage controls without WebGL")
        fallback.close()
        browser.close()
    assert not errors, errors
    report = {
        "passed": True,
        "checks": checks,
        "javascript_errors": errors,
        "scope": "Actual Chromium renders at three viewport widths. No mocked business endpoints.",
    }
    (output / "console-review.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

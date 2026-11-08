"""Exercise the real UI, including separate reviewer authentication.

Start an isolated server with AEGIS_DATA_DIR before running. No browser mocks.
"""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--data-dir", default=".local/browser-check")
    parser.add_argument("--output", default=".local/browser-results")
    args = parser.parse_args()
    credentials = json.loads((Path(args.data_dir) / "credentials.json").read_text())
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1060}, device_scale_factor=1
        )
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        chat_responses = []

        def capture_chat(response):
            if response.url.endswith("/api/ops/chat"):
                chat_responses.append({"status": response.status, "body": response.json()})
                (output / "chat-responses.json").write_text(json.dumps(chat_responses, indent=2), encoding="utf-8")

        page.on("response", capture_chat)
        page.goto(args.url)
        expect(page.locator("#loginDialog")).to_be_visible()
        page.locator("#username").fill(credentials["agent"]["username"])
        page.locator("#password").fill(credentials["agent"]["password"])
        page.locator("#loginSubmit").click()
        expect(page.locator("#loginDialog")).not_to_be_visible()
        expect(page.locator("#accountName")).to_contain_text("Priya")
        page.screenshot(path=str(output / "01-workspace.png"), full_page=True)
        page.locator('[data-prompt="Resolve ticket 101"]').click()
        page.locator("#chat").get_by_role(
            "button", name="Confirm & execute", exact=True
        ).last.click()
        expect(page.locator("#chat")).to_contain_text("→ resolved")
        page.locator(
            '[data-prompt="Export a customer report including email and phone"]'
        ).click()
        page.locator("#chat").get_by_role(
            "button", name="Request manager approval"
        ).last.click()
        expect(page.locator("#chat")).to_contain_text("Awaiting manager approval")
        page.locator('[data-view="approvals"]').click()
        page.locator("#managerLogin").click()
        page.locator("#password").fill(credentials["manager"]["password"])
        page.locator("#loginSubmit").click()
        expect(page.locator("#managerLogin")).to_contain_text("authenticated")
        page.screenshot(path=str(output / "02-approval.png"), full_page=True)
        page.get_by_role("button", name="Approve exact action").first.click()
        page.get_by_role("button", name="Test changed destination").first.click()
        expect(page.locator("#chat")).to_contain_text("Action blocked")
        page.locator('[data-view="approvals"]').click()
        page.get_by_role("button", name="Execute approved action").first.click()
        expect(page.locator("#chat")).to_contain_text("Download verified CSV")
        with page.expect_download() as info:
            page.locator("#chat").get_by_role(
                "button", name="Download verified CSV"
            ).last.click()
        report = output / "verified-report.csv"
        info.value.save_as(report)
        assert "email" in report.read_text() and "@example.test" in report.read_text()
        page.locator('[data-view="approvals"]').click()
        page.get_by_role("button", name="Test approval replay").first.click()
        expect(page.locator("#chat")).to_contain_text("consumed")
        page.locator('[data-view="checks"]').click()
        page.locator("#externalCheck").click()
        expect(page.locator("#checkResults")).to_contain_text("DATA-002 prohibits")
        page.locator("#tamperCheck").click()
        expect(page.locator("#checkResults")).to_contain_text(
            "differ from this proposal"
        )
        page.locator("#replayCheck").click()
        expect(page.locator("#checkResults")).to_contain_text("Replays are blocked")
        page.locator('[data-view="activity"]').click()
        expect(page.locator("#auditStatus")).to_contain_text(
            "Local audit chain verified"
        )
        page.screenshot(path=str(output / "03-evidence.png"), full_page=True)
        page.locator('[data-view="policies"]').click()
        expect(page.locator("#policies")).to_contain_text("Exact-action approval")
        page.locator('[data-view="assistant"]').click()
        page.reload()
        expect(page.locator("#accountName")).to_contain_text("Priya")
        expect(page.locator("#ticketMini")).to_contain_text("resolved")
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=str(output / "04-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
            "Mobile page overflows horizontally"
        )
        assert not errors, errors
        browser.close()
    result = {
        "browser": "Chromium",
        "checks": [
            "agent login",
            "actual ticket update",
            "separate manager login",
            "approved-action tampering denied",
            "exact approval",
            "real CSV download",
            "approval replay denied",
            "external destination denied",
            "proposal tampering denied",
            "proposal replay denied",
            "audit verification",
            "policy evidence",
            "refresh persistence",
            "mobile viewport",
            "no JavaScript errors",
        ],
        "passed": True,
        "screenshots": str(output),
    }
    (output / "browser-results.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

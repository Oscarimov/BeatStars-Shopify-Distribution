"""
Tiny self-test used by setup_playwright.bat and build_all.py: confirms
Playwright can actually drive the real, installed Google Chrome (channel=
"chrome"), not just that the files exist on disk. Exits 0 on success, 1 on
failure (prints the error).

This matches uploader.py's real runtime path exactly: the tool never
launches Playwright's own bundled Chromium, only the user's real Chrome
(needed so Shopify doesn't flag the login page as automated - see
login_shopify_chrome.bat / README).
"""
import sys
import tempfile

from playwright.sync_api import sync_playwright


def main() -> int:
    try:
        with sync_playwright() as p:
            with tempfile.TemporaryDirectory() as tmp_profile:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=tmp_profile,
                    channel="chrome",
                    headless=True,
                    args=["--no-sandbox"],
                )
                context.close()
    except Exception as e:
        print(f"[verify_playwright] Launch failed: {e}")
        return 1

    print("[verify_playwright] OK - Chrome launched successfully via Playwright")
    return 0


if __name__ == "__main__":
    sys.exit(main())

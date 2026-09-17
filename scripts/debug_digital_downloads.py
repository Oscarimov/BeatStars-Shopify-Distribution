"""
Diagnostic script — READ ONLY exploration of the Shopify "Digital Downloads"
app UI on a real product page. It never clicks Save/Submit and never uploads
files: it only navigates, screenshots, and dumps DOM info so we can see what
changed in the app's UI without guessing.

Usage:
    python debug_digital_downloads.py [product_gid_or_numeric_id]

If no product id is given, it picks the first product in the store.

Everything is written to scripts/debug_dumps/ (gitignored).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from uploader import ShopifyGraphQLUploader

DUMP_DIR = Path(__file__).parent / "debug_dumps"


async def dump_frame(frame, label: str, dump_dir: Path):
    info = {"url": frame.url, "name": frame.name}
    try:
        info["title"] = await frame.title()
    except Exception as e:
        info["title"] = f"<error: {e}>"

    try:
        html = await frame.content()
        (dump_dir / f"{label}.html").write_text(html, encoding="utf-8")
        info["html_length"] = len(html)
    except Exception as e:
        info["html_error"] = str(e)

    try:
        file_inputs = await frame.locator('input[type="file"]').all()
        inputs_info = []
        for idx, fi in enumerate(file_inputs):
            entry = {"index": idx}
            try:
                entry["id"] = await fi.get_attribute("id")
                entry["name"] = await fi.get_attribute("name")
                entry["accept"] = await fi.get_attribute("accept")
                parent_text = await fi.evaluate("el => el.closest('label, div, section')?.textContent?.slice(0,200)")
                entry["nearby_text"] = parent_text
            except Exception as e:
                entry["error"] = str(e)
            inputs_info.append(entry)
        info["file_inputs"] = inputs_info
    except Exception as e:
        info["file_inputs_error"] = str(e)

    try:
        buttons = await frame.locator("button, a[role='button'], [role='menuitem']").all()
        texts = []
        for b in buttons[:80]:
            try:
                t = (await b.inner_text()).strip()
                if t:
                    texts.append(t)
            except Exception:
                continue
        info["clickable_texts"] = texts
    except Exception as e:
        info["clickable_texts_error"] = str(e)

    return info


async def main_async():
    DUMP_DIR.mkdir(exist_ok=True)
    summary = {}

    uploader = ShopifyGraphQLUploader("config.json", beats_folder=Path(DUMP_DIR))

    print("🔐 Logging into Shopify (reusing existing automation)...")
    uploader.login_to_shopify()

    if not await uploader.verify_and_refresh_session():
        print("❌ Could not establish a valid session")
        return

    page = uploader.page

    # Resolve which product to inspect
    product_arg = sys.argv[1] if len(sys.argv) > 1 else None
    if product_arg:
        product_gid = product_arg if product_arg.startswith("gid://") else f"gid://shopify/Product/{product_arg}"
        product_title = "(from CLI arg)"
    else:
        collection_id = uploader.config.get("collection_id")
        result = uploader.graphql_request(
            """
            query($id: ID!) {
                collection(id: $id) {
                    products(first: 1, sortKey: UPDATED_AT, reverse: true) {
                        edges { node { id title } }
                    }
                }
            }
            """,
            {"id": collection_id}
        )
        edges = (((result or {}).get("data", {}) or {}).get("collection", {}) or {}).get("products", {}).get("edges", [])
        if not edges:
            print(f"❌ No products found in the configured collection ({collection_id})")
            return
        product_gid = edges[0]["node"]["id"]
        product_title = edges[0]["node"]["title"]

    summary["product_gid"] = product_gid
    summary["product_title"] = product_title
    print(f"🎯 Inspecting product: {product_title} ({product_gid})")

    numeric_id = product_gid.split("/")[-1]
    product_url = f"https://admin.shopify.com/store/{uploader.store_url.replace('.myshopify.com', '')}/products/{numeric_id}"
    summary["product_url"] = product_url

    await page.goto(product_url, timeout=30000, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)
    await page.screenshot(path=str(DUMP_DIR / "01_product_page.png"), full_page=True)
    (DUMP_DIR / "01_product_page.html").write_text(await page.content(), encoding="utf-8")

    # Dump every clickable text on the page BEFORE opening any menu — lets us
    # see if "More actions" itself changed name/location.
    top_level_texts = []
    try:
        els = await page.locator("button, a[role='button']").all()
        for el in els[:120]:
            try:
                t = (await el.inner_text()).strip()
                if t:
                    top_level_texts.append(t)
            except Exception:
                continue
    except Exception as e:
        top_level_texts = [f"<error: {e}>"]
    summary["top_level_clickable_texts"] = top_level_texts

    # Try the known "More actions" entry point
    more_actions_found = False
    try:
        more_actions = page.locator("button:has-text('More actions')").first
        await more_actions.wait_for(state="visible", timeout=8000)
        await more_actions.click()
        more_actions_found = True
        await page.wait_for_timeout(1000)
    except Exception as e:
        summary["more_actions_error"] = str(e)

    summary["more_actions_found"] = more_actions_found
    await page.screenshot(path=str(DUMP_DIR / "02_after_more_actions.png"), full_page=True)

    menu_texts = []
    try:
        items = await page.locator("[role='menuitem'], a, button").all()
        for it in items[:150]:
            try:
                t = (await it.inner_text()).strip()
                if t:
                    menu_texts.append(t)
            except Exception:
                continue
    except Exception as e:
        menu_texts = [f"<error: {e}>"]
    summary["menu_texts_after_more_actions"] = menu_texts

    # Try to find & click something related to "digital file" / "digital download"
    digital_link_found = False
    try:
        digital_link = page.locator(
            "a:has-text('digital file'), a:has-text('Digital file'), "
            "a:has-text('digital download'), a:has-text('Digital Download'), "
            "button:has-text('digital file'), button:has-text('Digital file')"
        ).first
        await digital_link.wait_for(state="visible", timeout=6000)
        await digital_link.click()
        digital_link_found = True
        await page.wait_for_timeout(4000)
    except Exception as e:
        summary["digital_link_error"] = str(e)

    summary["digital_link_found"] = digital_link_found
    await page.screenshot(path=str(DUMP_DIR / "03_after_digital_click.png"), full_page=True)
    (DUMP_DIR / "03_after_digital_click.html").write_text(await page.content(), encoding="utf-8")

    # Dump every frame on the page now
    frames_info = []
    for i, frame in enumerate(page.frames):
        frames_info.append(await dump_frame(frame, f"frame_{i}", DUMP_DIR))
    summary["frames"] = frames_info

    (DUMP_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Diagnostic dump written to: {DUMP_DIR}")
    print("   Files: 01_product_page.png/.html, 02_after_more_actions.png,")
    print("          03_after_digital_click.png/.html, frame_*.html, summary.json")

    await uploader.close_playwright()


def main():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(main_async())


if __name__ == "__main__":
    main()

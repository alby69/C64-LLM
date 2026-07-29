import os
import time
from playwright.sync_api import sync_playwright, expect

def run_verification():
    print("Starting Playwright...")
    os.makedirs("/home/jules/verification", exist_ok=True)

    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Navigating to http://localhost:7860 ...")
        page.goto("http://localhost:7860")

        # Wait for the main block to be loaded
        print("Waiting for page load...")
        page.wait_for_timeout(10000)

        # Take a screenshot of the Chat tab
        print("Taking Chat tab screenshot...")
        page.screenshot(path="/home/jules/verification/chat_tab.png")

        # Click on Monaco Editor tab
        print("Clicking Retro Editor & Linter tab...")
        page.get_by_role("tab", name="Retro Editor & Linter").first.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path="/home/jules/verification/retro_editor_tab.png")

        # Click on Vice Emulator tab
        print("Clicking Emulatore VICE WASM tab...")
        page.get_by_role("tab", name="Emulatore VICE WASM").first.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path="/home/jules/verification/vice_emulator_tab.png")

        # Click on Asset Gallery tab
        print("Clicking Galleria Asset Visivi tab...")
        page.get_by_role("tab", name="Galleria Asset Visivi").first.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path="/home/jules/verification/asset_gallery_tab.png")

        # Click on Memory Map tab
        print("Clicking Mappa Memoria Interattiva tab...")
        page.get_by_role("tab", name="Mappa Memoria Interattiva").first.click(force=True)
        page.wait_for_timeout(3000)
        page.screenshot(path="/home/jules/verification/memory_map_tab.png")

        browser.close()
        print("Playwright verification finished!")

if __name__ == "__main__":
    run_verification()

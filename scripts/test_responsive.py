import asyncio
from playwright.async_api import async_playwright
import os
import time

async def capture_screenshots():
    # Setup paths
    base_dir = "/Users/muradbakirov/.gemini/antigravity/brain/05545778-74ee-4c3a-a780-60fb005e5c7a/"
    desktop_dashboard = os.path.join(base_dir, "desktop_dashboard_final.png")
    desktop_expenses = os.path.join(base_dir, "desktop_expenses_final.png")
    mobile_expenses = os.path.join(base_dir, "mobile_expenses_final.png")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop Context
        desktop_context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        desktop_page = await desktop_context.new_page()
        
        # Dashboard Desktop
        await desktop_page.goto("http://127.0.0.1:8000/dashboard/")
        await desktop_page.wait_for_selector(".categories-grid")
        time.sleep(1) # wait for animations
        await desktop_page.screenshot(path=desktop_dashboard, full_page=True)
        print(f"Captured Desktop Dashboard: {desktop_dashboard}")
        
        # Expenses Desktop
        await desktop_page.goto("http://127.0.0.1:8000/expenses/")
        await desktop_page.wait_for_selector(".desktop-form-grid")
        time.sleep(1)
        await desktop_page.screenshot(path=desktop_expenses, full_page=True)
        print(f"Captured Desktop Expenses: {desktop_expenses}")
        await desktop_context.close()
        
        # 2. Mobile Context
        mobile_context = await browser.new_context(
            viewport={'width': 390, 'height': 844}
        )
        mobile_page = await mobile_context.new_page()
        
        # Expenses Mobile
        await mobile_page.goto("http://127.0.0.1:8000/expenses/")
        time.sleep(1)
        await mobile_page.screenshot(path=mobile_expenses, full_page=True)
        print(f"Captured Mobile Expenses: {mobile_expenses}")
        await mobile_context.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_screenshots())

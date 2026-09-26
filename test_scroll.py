import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import re

async def main():
    url = f"https://yandex.ru/maps/?text={urllib.parse.quote('маникюр Казань')}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        with open("page_source.html", "w") as f:
            f.write(html)
            
        print("Done")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://yandex.ru/maps/org/ne_nogti/114154381768/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        links = await page.locator('a, button').all()
        data = []
        for el in links:
            try:
                href = await el.get_attribute('href')
                aria = await el.get_attribute('aria-label')
                title = await el.get_attribute('title')
                cls = await el.get_attribute('class')
                text = await el.inner_text()
                if (href and 'yandex' not in href) or (aria and 'Сайт' in aria):
                    data.append({'href': href, 'aria': aria, 'title': title, 'class': cls, 'text': text})
            except:
                pass
        print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())

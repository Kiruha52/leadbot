import asyncio
from playwright.async_api import async_playwright
import re

async def main():
    url = "https://yandex.ru/maps/?text=Nails%20Nastasi%20Казань"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        show_phone = page.locator('div, span, button').filter(has_text=re.compile(r"Показать телефон", re.IGNORECASE))
        count = await show_phone.count()
        print(f"Found 'Показать телефон' {count} times")
        if count > 0:
            await show_phone.first.click()
            await page.wait_for_timeout(1000)
            
        new_phone_elem = page.locator('a[href^="tel:"]')
        new_phone = ""
        if await new_phone_elem.count() > 0:
            new_phone = await new_phone_elem.first.get_attribute('href')
            
        print(f"Extracted phone: '{new_phone}'")
        
if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://yandex.ru/maps/org/114154381768/" # fioletovo
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Print all buttons with text
        btns = await page.locator('button, .button').all()
        for b in btns:
            try:
                text = await b.inner_text()
                if text.strip():
                    print("Button text:", text.strip().replace('\n', ' '))
            except:
                pass
                
        # Try to extract phone
        phones = await page.locator('div[class*="phone"]').all()
        for p in phones:
            try:
                html = await p.evaluate('node => node.outerHTML')
                print("Phone DOM:", html)
            except:
                pass
                
if __name__ == "__main__":
    asyncio.run(main())

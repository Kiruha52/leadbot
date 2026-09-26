import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def main():
    url = f"https://yandex.ru/maps/?text={urllib.parse.quote('студия ногтей Казань')}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        try:
            await page.wait_for_selector('li.search-snippet-view a[href*="/org/"], .captcha-form', timeout=15000)
        except Exception:
            pass

        hrefs = set()
        scroll_container = page.locator('.scroll__container, .search-list-view__list').first
        if await scroll_container.count() > 0:
            await scroll_container.click()
            for scroll_idx in range(50):
                links_loc = page.locator('li.search-snippet-view a[href*="/org/"]')
                count = await links_loc.count()
                for i in range(count):
                    try:
                        href = await links_loc.nth(i).get_attribute('href')
                        if href and 'reviews' not in href and 'gallery' not in href and 'features' not in href:
                            hrefs.add(urllib.parse.urljoin("https://yandex.ru", href.split('?')[0]))
                    except:
                        pass
                print(f"Scroll {scroll_idx}: {count} links in DOM, {len(hrefs)} unique total")
                try:
                    await page.locator('li.search-snippet-view').last.hover(timeout=1000)
                    await page.mouse.wheel(0, 2000)
                except:
                    pass
                await page.wait_for_timeout(800)
                
        print(f"Final extracted: {len(hrefs)}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright
import urllib.parse
from parser import is_valid_lead

async def debug_scrape(city: str, niche: str):
    query = f"{niche} {city}"
    url = f"https://yandex.ru/maps/?text={urllib.parse.quote(query)}"
    
    print("Starting Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            print(f"Navigating to {url}...")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            await page.wait_for_selector('li.search-snippet-view', timeout=15000)
            
            scroll_container = page.locator('.scroll__scroll').first
            if await scroll_container.count() > 0:
                for _ in range(5):
                    await scroll_container.evaluate('node => node.scrollBy(0, 5000)')
                    await page.wait_for_timeout(1000)

            links_loc = page.locator('li.search-snippet-view a[href*="/org/"]')
            count = await links_loc.count()
            
            hrefs = set()
            for i in range(count):
                href = await links_loc.nth(i).get_attribute('href')
                if href and 'reviews' not in href and 'gallery' not in href and 'features' not in href:
                    hrefs.add(urllib.parse.urljoin("https://yandex.ru", href.split('?')[0]))
                    
            hrefs = list(hrefs)[:15]
            print(f"Found {len(hrefs)} URLs to check out of {count} links")
            
            for href in hrefs:
                try:
                    await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    
                    await page.wait_for_selector('h1', timeout=5000)
                    title = await page.locator('h1').first.inner_text()
                    
                    show_phone_btn = page.locator('div[class*="button"]:has-text("Показать"), div[class*="phones-view"]:has-text("Показать"), span:has-text("Показать телефон")')
                    if await show_phone_btn.count() > 0:
                        await show_phone_btn.first.click()
                        await page.wait_for_timeout(1000)
                    
                    phone_elem = page.locator('[class*="phone-number"], a[href^="tel:"]')
                    phone = "NO_PHONE"
                    if await phone_elem.count() > 0:
                        phone = await phone_elem.first.inner_text()
                        
                    site_loc = page.locator('.business-urls-view__link, a[class*="url"], a[class*="site"]')
                    site = "NO_SITE"
                    for j in range(await site_loc.count()):
                        href_attr = await site_loc.nth(j).get_attribute('href')
                        if href_attr and 'yandex' not in href_attr and ('http' in href_attr or 'vk.' in href_attr or 't.me' in href_attr):
                            site = await site_loc.nth(j).inner_text()
                            break
                            
                    print(f"Title: '{title}' | Phone: '{phone}' | Site: '{site}' | Valid: {is_valid_lead(title, site, phone)}")
                    
                except Exception as e:
                    print(f"Error on {href}: {e}")
                    
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape("Казань", "маникюр"))

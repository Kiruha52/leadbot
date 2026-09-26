import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import re
import os
from tg_resolver import resolve_tg_usernames_batch, normalize_phone

TG_ENABLED = os.getenv('TG_ENABLED', 'true').lower() == 'true'

async def scrape_yandex_maps(city: str, niche: str, checked_urls: set[str] = None) -> tuple[list[tuple[str, str, str | None]], list[str], bool]:
    if checked_urls is None:
        checked_urls = set()
        
    query = f"{niche} {city}"
    url = f"https://yandex.ru/maps/?text={urllib.parse.quote(query)}"
    
    results = []
    newly_checked_urls = []
    is_exhausted = False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            try:
                await page.wait_for_selector('li.search-snippet-view a[href*="/org/"], .captcha-form', timeout=15000)
            except Exception:
                pass
                
            if await page.locator('.captcha-form').count() > 0 or 'showcaptcha' in page.url:
                raise Exception("Поймали капчу от Яндекса. Попробуйте позже.")

            # Extract URLs while scrolling because Yandex Maps virtualizes the DOM
            hrefs = set()
            scroll_container = page.locator('.scroll__container, .search-list-view__list').first
            if await scroll_container.count() > 0:
                await scroll_container.click()
                previous_len = 0
                unchanged_count = 0
                for _ in range(500): # Максимум 500 скроллов
                    try:
                        hrefs_batch = await page.locator('li.search-snippet-view a[href*="/org/"]').evaluate_all('elements => elements.map(el => el.getAttribute("href"))')
                        for href in hrefs_batch:
                            if href and 'reviews' not in href and 'gallery' not in href and 'features' not in href:
                                hrefs.add(urllib.parse.urljoin("https://yandex.ru", href.split('?')[0]))
                    except Exception as e:
                        pass
                            
                    if len(hrefs) == previous_len:
                        unchanged_count += 1
                        if unchanged_count >= 15: # Если 15 скроллов подряд не принесли новых ссылок - конец списка
                            break
                    else:
                        unchanged_count = 0
                        previous_len = len(hrefs)
                        
                    # Stop scrolling early if we have enough NEW urls to check
                    new_urls_count = sum(1 for h in hrefs if h not in checked_urls)
                    if new_urls_count >= 100:
                        break
                        
                    try:
                        await page.evaluate('''() => {
                            const container = document.querySelector('.scroll__container') || document.querySelector('.search-list-view__list');
                            if (container) container.scrollBy(0, 3000);
                        }''')
                    except:
                        pass
                    await page.wait_for_timeout(800)
            
            hrefs = list(hrefs)
            print(f"Extracted {len(hrefs)} unique URLs")
            
            # Filter out already checked URLs
            hrefs_to_check = [h for h in hrefs if h not in checked_urls]
            print(f"URLs to check after filtering: {len(hrefs_to_check)}")
            
            if not hrefs_to_check:
                is_exhausted = True
            
            for href in hrefs_to_check:
                newly_checked_urls.append(href)
                try:
                    await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                    
                    # wait for H1
                    try:
                        await page.wait_for_selector('h1', timeout=5000)
                    except:
                        pass
                        
                    title_elem = page.locator('h1').first
                    title = await title_elem.inner_text() if await title_elem.count() > 0 else ""
                    if not title:
                        print(f"No title found for {href}")
                        continue
                        
                    # Click anything that says "Показать"
                    show_btns = page.locator('div, span, button').filter(has_text=re.compile(r"Показать", re.IGNORECASE))
                    if await show_btns.count() > 0:
                        for btn_idx in range(min(await show_btns.count(), 3)):
                            try:
                                await show_btns.nth(btn_idx).click(timeout=1000)
                            except:
                                pass
                        await page.wait_for_timeout(1000)
                        
                    html = await page.content()
                    
                    # Get phone
                    phone_elem = page.locator('[class*="phone-number"], a[href^="tel:"], .business-contacts-view__phone')
                    phone = ""
                    if await phone_elem.count() > 0:
                        for idx in range(await phone_elem.count()):
                            p_text = await phone_elem.nth(idx).inner_text()
                            if any(char.isdigit() for char in p_text):
                                phone = p_text
                                break
                    
                    # Get site (globe button or external links)
                    site_loc = page.locator(
                        '.business-urls-view__link, '
                        '.business-urls-view__text, '
                        'a[class*="business-url"], '
                        'a[class*="url-view"], '
                        'a[href^="http"]:not([href*="yandex"])[class*="link"]'
                    )
                    site = ""
                    for j in range(await site_loc.count()):
                        href_attr = await site_loc.nth(j).get_attribute('href')
                        if href_attr and 'yandex' not in href_attr and href_attr.startswith('http'):
                            site = href_attr
                            break
                    
                    # Detect delivery/order buttons — sign of a commercial business, not a private master
                    delivery_btn = page.locator('button, a, div').filter(
                        has_text=re.compile(r'Заказать доставку|Заказать букет|Заказать онлайн', re.IGNORECASE)
                    )
                    has_delivery_button = await delivery_btn.count() > 0
                    
                    print(f"Checking: {title}, phone: {phone}, site: {site}")
                    
                    # Filter
                    if is_valid_lead(title, site, phone, has_delivery_button):
                        results.append((title, phone, None))
                        print(f"-> VALID LEAD! ({len(results)})")
                    else:
                        print(f"-> INVALID")
                        
                except Exception as e:
                    print(f"Error on {href}: {e}")
                    continue
                    
        finally:
            await browser.close()
            
    # Check exhaustion: if we hit the end of the list without collecting 100 new URLs, we are exhausted.
    if len(hrefs_to_check) < 100:
        is_exhausted = True
        
    # Remove duplicates while preserving order
    unique_results = []
    seen = set()
    phones_to_check = []
    
    for title, phone, _ in results:
        if phone not in seen:
            seen.add(phone)
            unique_results.append((title, phone))
            phones_to_check.append(phone)
            
    # Batch resolve TG usernames (only if TG_ENABLED)
    if TG_ENABLED:
        tg_user_map = await resolve_tg_usernames_batch(phones_to_check)
    else:
        tg_user_map = {}
    
    final_results = []
    for title, phone in unique_results:
        norm_phone = normalize_phone(phone) if phone else None
        tg_data = tg_user_map.get(norm_phone) if norm_phone else None
        
        is_registered = True if tg_data is not None else (False if TG_ENABLED else None)
        tg_username = tg_data.get('username') if tg_data else None
        
        final_results.append((title, phone, tg_username, is_registered))
    return final_results, newly_checked_urls, is_exhausted

def is_valid_lead(title: str, site: str, phone: str, has_delivery_button: bool = False) -> bool:
    if not phone:
        return False
    
    # "Заказать доставку" button = large commercial business, not a private master
    if has_delivery_button:
        return False
        
    if site:
        # Разрешенные домены (агрегаторы, онлайн-запись, соцсети, бесплатные конструкторы Яндекса).
        # Если ссылка ведет сюда, значит полноценного личного сайта у мастера нет, и он нам подходит!
        allowed_domains = [
            'dikidi.', 'taplink.', 'mst.link', 'vk.', 't.me', 'wa.me', 'instagram.', 
            'clients.site', 'yclients.', 'beautybox.', 'nethouse.', 'viber.', 'whatsapp.'
        ]
        is_allowed = any(domain in site for domain in allowed_domains)
        if not is_allowed:
            return False # У них есть реальный сайт (свой домен) - пропускаем
            
    return True

if __name__ == "__main__":
    res = asyncio.run(scrape_yandex_maps("Москва", "маникюр"))
    print(res)

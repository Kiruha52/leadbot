import asyncio
import os
import sys

# Unbuffer stdout
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

from parser import scrape_yandex_maps
from tg_resolver import user_client

async def test():
    print("Starting client...")
    await user_client.start()
    print("Started client. Scraping...")
    leads, _, _ = await scrape_yandex_maps("Екатеринбург", "Ногтевая студия", set())
    print("Scrape complete!")
    
    with_tg = 0
    with_username = 0
    
    for title, phone, username, registered in leads:
        if registered:
            with_tg += 1
            if username:
                with_username += 1
                
    print(f"Total leads: {len(leads)}")
    print(f"Registered in TG: {with_tg}")
    print(f"With username: {with_username}")

if __name__ == "__main__":
    asyncio.run(test())

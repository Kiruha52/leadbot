import asyncio
from parser import scrape_yandex_maps
from tg_resolver import user_client

async def test():
    await user_client.start()
    leads, _, _ = await scrape_yandex_maps("Екатеринбург", "Ногтевая студия", set())
    
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

import asyncio
from parser import scrape_yandex_maps

async def main():
    print("Starting scrape...")
    results = await scrape_yandex_maps("Казань", "маникюр")
    print(f"Scrape finished. Found {len(results)} results:")
    for res in results:
        print(res)

if __name__ == "__main__":
    asyncio.run(main())

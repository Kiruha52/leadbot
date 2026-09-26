import asyncio
import qrcode
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv('TELEGRAM_API_ID', 10840))
API_HASH = os.getenv('TELEGRAM_API_HASH', '33c45224029d59cb3ad0c16134215aeb')
ARTIFACT_IMG = "/Users/kirill/.gemini/antigravity-ide/brain/013c68a9-2159-4f57-ac0b-b5ea948354d2/qr_code.png"

async def main():
    client = TelegramClient('local_user_session', API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        print("ALREADY_AUTHORIZED")
        await client.disconnect()
        return

    qr_login = await client.qr_login()

    try:
        attempts = 0
        while not await client.is_user_authorized() and attempts < 10:
            attempts += 1
            # Generate QR code image
            img = qrcode.make(qr_login.url)
            img.save(ARTIFACT_IMG)
            print("QR Code updated at", ARTIFACT_IMG)
            
            try:
                # Wait for the user to scan
                await asyncio.wait_for(qr_login.wait(), timeout=20)
                break
            except asyncio.TimeoutError:
                print("QR code expired, refreshing...")
                await qr_login.recreate()

        if await client.is_user_authorized():
            print("Успешная авторизация по QR коду!")
        else:
            print("Превышено время ожидания.")
    except Exception as e:
        print("Ошибка:", e)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

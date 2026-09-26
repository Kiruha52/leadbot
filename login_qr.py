import asyncio
import qrcode
from telethon import TelegramClient
import os
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv('TELEGRAM_API_ID', 2040))
API_HASH = os.getenv('TELEGRAM_API_HASH', 'b18441a1ff607e10a989891a5462e627')

async def main():
    client = TelegramClient('local_user_session', API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        print("ALREADY_AUTHORIZED")
        await client.disconnect()
        return

    qr_login = await client.qr_login()

    try:
        while not await client.is_user_authorized():
            # Generate QR code image
            img = qrcode.make(qr_login.url)
            img.save("tg_qr.png")
            print("QR-код обновлен! Открой файл tg_qr.png на рабочем столе и отсканируй его через приложение Telegram (Настройки -> Устройства -> Подключить устройство).")
            
            try:
                # Wait 15 seconds
                await asyncio.wait_for(qr_login.wait(), timeout=15)
                break
            except asyncio.TimeoutError:
                print("QR-код устарел, обновляю...")
                await qr_login.recreate()

        print("Успешная авторизация по QR коду!")
    except Exception as e:
        print("Ошибка:", e)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

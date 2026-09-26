import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import sys
import os

load_dotenv()
API_ID = int(os.getenv('TELEGRAM_API_ID', 2040))
API_HASH = os.getenv('TELEGRAM_API_HASH', 'b18441a1ff607e10a989891a5462e627')
PHONE = "+79372743377"

async def main():
    if len(sys.argv) < 2:
        print("Provide code as argument")
        return
    
    code = sys.argv[1]
    client = TelegramClient(
        "/Users/kirill/Desktop/приложения/lead_bot/local_user_session",
        API_ID,
        API_HASH,
        device_model="iPhone 13 Pro",
        system_version="iOS 15.1",
        app_version="8.4"
    )
    try:
        await client.start(phone=PHONE, code_callback=lambda: code)
        print("Signed in successfully!")
    except Exception as e:
        print("Failed:", e)

asyncio.run(main())

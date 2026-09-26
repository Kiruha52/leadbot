import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv
import os

load_dotenv()
API_ID = int(os.getenv('TELEGRAM_API_ID', 2040))
API_HASH = os.getenv('TELEGRAM_API_HASH', 'b18441a1ff607e10a989891a5462e627')
PHONE = "+79372743377"

async def main():
    client = TelegramClient("/Users/kirill/Desktop/приложения/lead_bot/local_user_session", API_ID, API_HASH)
    await client.connect()
    is_authorized = await client.is_user_authorized()
    print("Is authorized?", is_authorized)
    if not is_authorized:
        print("Sending code to", PHONE)
        await client.send_code_request(PHONE)
        print("Code requested successfully!")

asyncio.run(main())

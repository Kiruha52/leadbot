from telethon import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
import re
import asyncio
import sqlite3
import os

API_ID = int(os.getenv('TELEGRAM_API_ID', 10840))
API_HASH = os.getenv('TELEGRAM_API_HASH', '33c45224029d59cb3ad0c16134215aeb')
SOURCE_SESSION = "/Users/kirill/Desktop/тг бот/tgnumber/user_session.session"
LOCAL_SESSION = "/Users/kirill/Desktop/приложения/lead_bot/local_user_session.session"



user_client = TelegramClient("/Users/kirill/Desktop/приложения/lead_bot/local_user_session", API_ID, API_HASH)

async def start_tg_client():
    await user_client.connect()
    if not await user_client.is_user_authorized():
        raise RuntimeError("Telegram user session is not authorized. Please run login_qr_agent.py first.")
    print("Telegram client started for lead_bot.")

async def stop_tg_client():
    await user_client.disconnect()
    print("Telegram client stopped.")

def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7 or len(digits) > 15:
        return None
    return "+" + digits

async def resolve_tg_usernames_batch(phones: list[str]) -> dict[str, dict]:
    contacts = []
    idx_to_phone = {}
    for idx, p in enumerate(phones):
        norm = normalize_phone(p)
        if norm:
            contacts.append(InputPhoneContact(client_id=idx, phone=norm, first_name="TMP", last_name=""))
            idx_to_phone[idx] = norm
            
    if not contacts:
        return {}
        
    try:
        user_id_to_username = {}
        user_map = {}
        found_users = []
        
        # Telegram silently ignores large batches. Chunk into groups of 5.
        chunk_size = 5
        for i in range(0, len(contacts), chunk_size):
            chunk = contacts[i:i + chunk_size]
            result = await user_client(ImportContactsRequest(chunk))
            
            for user in result.users:
                if getattr(user, 'username', None):
                    user_id_to_username[user.id] = user.username
                    
                if getattr(user, 'phone', None):
                    phone_with_plus = "+" + user.phone
                    user_map[phone_with_plus] = {'registered': True, 'username': getattr(user, 'username', None)}
                    
                found_users.append(user)
                
            for imp in result.imported:
                norm_phone = idx_to_phone.get(imp.client_id)
                username = user_id_to_username.get(imp.user_id)
                if norm_phone:
                    user_map[norm_phone] = {'registered': True, 'username': username}
                    
            await asyncio.sleep(1) # Delay between chunks to prevent flood limits
            
        if found_users:
            try:
                # Delete in chunks as well to avoid limits
                for i in range(0, len(found_users), 50):
                    await user_client(DeleteContactsRequest(id=found_users[i:i+50]))
            except Exception:
                pass
                
        return user_map
    except Exception as e:
        print(f"Error resolving TG usernames batch: {e}")
        return {}

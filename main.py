import asyncio
import os
import logging
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from constants import TOP_100_CITIES, NICHES
from parser import scrape_yandex_maps
from state_manager import load_state, save_state
from tg_resolver import start_tg_client, stop_tg_client
TG_ENABLED = True  # TG session is active

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_bot_token_here":
    pass

bot = Bot(token=TELEGRAM_TOKEN) if TELEGRAM_TOKEN and TELEGRAM_TOKEN != "your_telegram_bot_token_here" else Bot(token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
dp = Dispatcher()

# FSM States
class LeadBotStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_niche = State()

def get_paginated_keyboard(items, page: int, prefix: str, items_per_page: int = 14, formatter=None):
    buttons = []
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    current_items = items[start_idx:end_idx]
    
    # 2 columns per row
    for i in range(0, len(current_items), 2):
        row = []
        item1 = current_items[i]
        idx1 = start_idx + i
        text1 = formatter(item1) if formatter else item1
        row.append(InlineKeyboardButton(text=text1, callback_data=f"{prefix}_sel_{idx1}"))
        
        if i + 1 < len(current_items):
            item2 = current_items[i+1]
            idx2 = start_idx + i + 1
            text2 = formatter(item2) if formatter else item2
            row.append(InlineKeyboardButton(text=text2, callback_data=f"{prefix}_sel_{idx2}"))
            
        buttons.append(row)
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{prefix}_page_{page-1}"))
    if end_idx < len(items):
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"{prefix}_page_{page+1}"))
        
    if nav_row:
        buttons.append(nav_row)
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я бот для сбора лидов (частных мастеров) с Яндекс Карт.\n"
        "Выбери город из списка ниже (листай кнопками):",
        reply_markup=get_paginated_keyboard(TOP_100_CITIES, 0, "city")
    )
    await state.set_state(LeadBotStates.waiting_for_city)

@dp.callback_query(F.data.startswith("city_page_"))
async def process_city_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await callback.message.edit_reply_markup(
        reply_markup=get_paginated_keyboard(TOP_100_CITIES, page, "city")
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("city_sel_"), StateFilter(LeadBotStates.waiting_for_city))
async def process_city_selection(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[2])
    city = TOP_100_CITIES[idx]
    await state.update_data(city=city)
    
    state_data = load_state()
    def format_niche(niche):
        key = f"{city}_{niche}"
        data = state_data.get(key)
        if not data:
            return niche
        leads = data.get("total_leads_found", 0)
        searches = data.get("search_count", 0)
        exhausted = data.get("exhausted", False)
        
        if exhausted:
            return f"{niche} (Найдено {leads}, больше нет)"
        else:
            return f"{niche} (Найдено {leads}, есть еще)"
    
    await callback.message.edit_text(
        text=f"📍 Город выбран: **{city}**\n\n"
             "Теперь выбери нишу из списка ниже (или напиши текстом любую другую):",
        reply_markup=get_paginated_keyboard(NICHES, 0, "niche", formatter=format_niche),
        parse_mode="Markdown"
    )
    await state.set_state(LeadBotStates.waiting_for_niche)
    await callback.answer()

@dp.callback_query(F.data.startswith("niche_page_"))
async def process_niche_page(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[2])
    data = await state.get_data()
    city = data.get("city")
    
    state_data = load_state()
    def format_niche(niche):
        if not city:
            return niche
        key = f"{city}_{niche}"
        data = state_data.get(key)
        if not data:
            return niche
        leads = data.get("total_leads_found", 0)
        searches = data.get("search_count", 0)
        exhausted = data.get("exhausted", False)
        
        if exhausted:
            return f"{niche} (Найдено {leads}, больше нет)"
        else:
            return f"{niche} (Найдено {leads}, есть еще)"

    await callback.message.edit_reply_markup(
        reply_markup=get_paginated_keyboard(NICHES, page, "niche", formatter=format_niche)
    )
    await callback.answer()

background_tasks = set()

@dp.callback_query(F.data.startswith("niche_sel_"), StateFilter(LeadBotStates.waiting_for_niche))
async def process_niche_selection(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[2])
    niche = NICHES[idx]
    
    data = await state.get_data()
    city = data.get("city")
    
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    task = asyncio.create_task(start_parsing(callback.message, city, niche))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

@dp.message(StateFilter(LeadBotStates.waiting_for_niche))
async def process_niche_input(message: Message, state: FSMContext):
    niche = message.text.strip()
    data = await state.get_data()
    city = data.get("city")
    
    await state.clear()
    
    task = asyncio.create_task(start_parsing(message, city, niche))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

async def start_parsing(message: Message, city: str, niche: str):
    state_data = load_state()
    key = f"{city}_{niche}"
    
    if state_data.get(key, {}).get("exhausted", False):
        await message.answer(f"Все доступные лиды по нише '{niche}' в городе '{city}' уже собраны.")
        return

    await message.answer(
        f"Ищем нишу: {niche} в городе: {city}.\n"
        "Запускаю сканер. Бот проверит 100 новых карточек (пропуская уже проверенные) и пришлет всех подходящих лидов, которых сможет там найти! Это может занять некоторое время, я напишу как закончу!"
    )
    
    # Run the parser
    try:
        checked_urls = set(state_data.get(key, {}).get("checked_urls", []))
        results, newly_checked_urls, is_exhausted = await scrape_yandex_maps(city, niche, checked_urls)
        
        # Save state
        if key not in state_data:
            state_data[key] = {"checked_urls": [], "exhausted": False, "total_leads_found": 0, "search_count": 0}
        state_data[key]["checked_urls"].extend(newly_checked_urls)
        state_data[key]["exhausted"] = is_exhausted
        state_data[key]["total_leads_found"] = state_data[key].get("total_leads_found", 0) + len(results)
        state_data[key]["search_count"] = state_data[key].get("search_count", 0) + 1
        save_state(state_data)
        
        if not results:
            if is_exhausted:
                await message.answer("Не удалось найти новых лидов, все возможные варианты исчерпаны.")
            else:
                await message.answer("Не удалось найти подходящих частных мастеров по вашему запросу на этой странице. Попробуйте еще раз для поиска дальше.")
        else:
            chunks = []
            current_chunk = f"<b>Найдено {len(results)} лидов:</b>\n\n"
            
            for title, phone, tg_username, is_registered in results:
                digits = re.sub(r"\D", "", phone) if phone else ""
                lead_text = f"🏢 <b>Название:</b> {title}\n"
                if phone:
                    lead_text += f"📞 <b>Телефон:</b> {phone}\n"
                    
                    if digits:
                        wa_link = f"https://wa.me/{digits}"
                        lead_text += f"💬 <b>WhatsApp:</b> <a href=\"{wa_link}\">написать</a>\n"
                        
                    if is_registered:
                        if tg_username:
                            lead_text += f"✅ <b>Telegram:</b> Есть\n  Юзернейм: <a href=\"https://t.me/{tg_username}\">@{tg_username}</a>\n"
                        else:
                            tg_link = f"https://t.me/+{digits}"
                            lead_text += f"✅ <b>Telegram:</b> Есть\n  Связаться: <a href=\"{tg_link}\">написать</a>\n"
                    elif is_registered is False:
                        lead_text += f"❌ <b>Telegram:</b> Нет (или скрыт)\n"
                lead_text += "\n"
                
                if len(current_chunk) + len(lead_text) > 4000:
                    chunks.append(current_chunk)
                    current_chunk = lead_text
                else:
                    current_chunk += lead_text
                    
            if current_chunk:
                chunks.append(current_chunk)
                
            for chunk in chunks:
                await message.answer(chunk, parse_mode="HTML")
            
            if is_exhausted:
                await message.answer("🛑 <b>Внимание:</b> Все возможные лиды в этой нише и городе исчерпаны. Больше новых контактов найти не удастся.", parse_mode="HTML")
                
    except Exception as e:
        logging.error(f"Error while parsing: {e}")
        await message.answer(f"Произошла ошибка при парсинге. Возможно, Яндекс выдал капчу или изменилась структура сайта. Текст ошибки: {str(e)}")
        
    finally:
        await message.answer("Поиск завершен. Нажми /start чтобы начать заново.")

async def main():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "your_telegram_bot_token_here":
        print("ОШИБКА: Заполните TELEGRAM_TOKEN в файле .env перед запуском!")
        return
    if TG_ENABLED:
        dp.startup.register(start_tg_client)
        dp.shutdown.register(stop_tg_client)
    
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

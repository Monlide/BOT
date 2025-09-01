import logging
import json
import os
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMedia
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# === CONFIG ===
CONFIG_FILE = "connect.json"
USERS_FILE = "users.json"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === LOAD ENV ===
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === HELPERS ===
def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f)

def add_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)
    # добавляем админов в список
    for admin_id in ADMIN_IDS:
        if admin_id not in users:
            users.append(admin_id)
    save_users(users)

# === KEYBOARDS ===
def get_main_keyboard():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="⚡ Как получить прогноз?", callback_data="how")],
        [InlineKeyboardButton(text="🎁 Бонус от партнёров", callback_data="bookmakers")],
        [InlineKeyboardButton(text="🏠 На главный экран", callback_data="main")]
    ])
    return kb

def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩ Назад в меню", callback_data="main")]
        ]
    )

# === STATES ===
class BroadcastState(StatesGroup):
    ask_photo = State()
    wait_photo = State()
    wait_text = State()
    final_text = State()

# === HANDLERS ===
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    add_user(message.from_user.id)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    photo = FSInputFile("logo.png")
    await message.answer_photo(
        photo=photo,
        caption=config.get("main_text", "Добро пожаловать! 🚀"),
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "main")
async def callback_main(callback: types.CallbackQuery):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    photo = FSInputFile("logo.png")
    try:
        await callback.message.edit_media(
            InputMediaPhoto(media=photo, caption=config.get("main_text", "Добро пожаловать! 🚀")),
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        # если редактирование не вышло, отправляем новое меню и удаляем старое
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer_photo(
            photo=photo,
            caption=config.get("main_text", "Добро пожаловать! 🚀"),
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    await callback.message.edit_text(
        config.get("stats_text", "Статистика временно недоступна"),
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "how")
async def callback_how(callback: types.CallbackQuery):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    await callback.message.edit_text(
        config.get("how_text", "Информация недоступна"),
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "bookmakers")
async def callback_bookmakers(callback: types.CallbackQuery):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=config.get("bonus_btn1_text", "Бонус №1"), url=config.get("bonus_btn1_url", "https://google.com"))],
        [InlineKeyboardButton(text=config.get("bonus_btn2_text", "Бонус №2"), url=config.get("bonus_btn2_url", "https://google.com"))],
        [InlineKeyboardButton(text=config.get("bonus_btn3_text", "Бонус №3"), url=config.get("bonus_btn3_url", "https://google.com"))],
        [InlineKeyboardButton(text="↩ Вернуться в меню", callback_data="main")]
    ])
    photo = FSInputFile("logo.png")
    try:
        await callback.message.edit_media(
            InputMediaPhoto(media=photo, caption=config.get("bookmakers_text", "Выбирай бонус")),
            reply_markup=kb
        )
    except:
        await callback.message.edit_caption(
            caption=config.get("bookmakers_text", "Выбирай бонус"),
            reply_markup=kb
        )
    await callback.answer()

# === BROADCAST ===
@dp.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа.")
        return
    await message.answer("📢 Хочешь прикрепить картинку к рассылке? Напиши *да* или *нет*.", parse_mode="Markdown")
    await state.set_state(BroadcastState.ask_photo)

@dp.message(BroadcastState.ask_photo, F.text.lower() == "да")
async def ask_photo(message: types.Message, state: FSMContext):
    await message.answer("🖼 Пришли фото для рассылки:")
    await state.set_state(BroadcastState.wait_photo)

@dp.message(BroadcastState.ask_photo, F.text.lower() == "нет")
async def ask_text_only(message: types.Message, state: FSMContext):
    await message.answer("✍️ Введи текст для рассылки:")
    await state.set_state(BroadcastState.final_text)

@dp.message(BroadcastState.wait_photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await message.answer("✍️ Теперь введи подпись к фото:")
    await state.set_state(BroadcastState.wait_text)

@dp.message(BroadcastState.wait_text)
async def send_photo_broadcast(message: types.Message, state: FSMContext):
    data = await state.get_data()
    caption = message.text or ""
    users = load_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_photo(
                chat_id=uid,
                photo=data["photo"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
            sent += 1
        except Exception as e:
            logging.warning(f"send_photo to {uid} failed: {e}")
    await message.answer(f"✅ Рассылка завершена! Отправлено {sent} пользователям.")
    await state.clear()

@dp.message(BroadcastState.final_text)
async def send_text_broadcast(message: types.Message, state: FSMContext):
    text = message.text or ""
    users = load_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(
                uid,
                text,
                parse_mode="Markdown",
                reply_markup=get_back_keyboard()
            )
            sent += 1
        except Exception as e:
            logging.warning(f"send_text to {uid} failed: {e}")
    await message.answer(f"✅ Рассылка завершена! Отправлено {sent} пользователям.")
    await state.clear()

# === START ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))

import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import sqlite3

BOT_TOKEN = "8733911430:AAF0y4vZM-E1JoiS9PkgHSF8aBE5BcZsfzY"
ADMIN_ID = 8507520917  # Твой Telegram ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQLite) ---
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_user_balance(user_id: int) -> int:
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0

def update_user_balance(user_id: int, amount: int):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, balance) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    """, (user_id, amount, amount))
    conn.commit()
    conn.close()

# --- КОМАНДЫ БОТА ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    # Регистрируем в БД при старте
    update_user_balance(message.from_user.id, 0)
    bal = get_user_balance(message.from_user.id)
    await message.answer(f"✨ Welcome to Casino Limbo!\n\n💰 Ваш баланс: {bal} ₽")

@dp.message(Command("addbalance"))
async def add_balance_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        args = message.text.split()
        target_id = int(args[1])
        sum_amount = int(args[2])
        
        update_user_balance(target_id, sum_amount)
        new_bal = get_user_balance(target_id)
        
        await message.answer(f"✅ Баланс игрока {target_id} успешно пополнен на {sum_amount} ₽!\nТекущий баланс: {new_bal} ₽")
        
        # Уведомляем игрока
        try:
            await bot.send_message(target_id, f"💳 Ваш баланс пополнен на {sum_amount} ₽!")
        except:
            pass
    except Exception as e:
        await message.answer("❌ Ошибка! Используй формат: `/addbalance ID СУММА`\nПример: `/addbalance 8620735231 1000`", parse_mode="Markdown")

# --- API ДЛЯ MINI APP (HTTP Сервер) ---
async def handle_get_balance(request):
    try:
        user_id = int(request.query.get("user_id", 0))
        bal = get_user_balance(user_id)
        return web.json_response({"balance": bal}, headers={"Access-Control-Allow-Origin": "*"})
    except:
        return web.json_response({"balance": 0}, headers={"Access-Control-Allow-Origin": "*"})

# --- ЗАПУСК БОТА И ВЕБ-СЕРВЕРА ---
async def main():
    init_db()
    
    # Настраиваем API сервер
    app = web.Application()
    app.router.add_get("/api/balance", handle_get_balance)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    
    print("🚀 Запуск API сервера на порту 8080...")
    await site.start()
    
    print("🤖 Запуск Telegram бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
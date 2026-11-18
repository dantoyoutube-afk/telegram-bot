import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ваш токен бота
TOKEN = "9169950174:AAER5e6waegpMJNHOwjFqIjM6PTGC2Ksv6k"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Створюємо Flask-сервер для утримання сервісу активним
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот успішно працює і пінгується!"

def run_flask():
    # Render автоматично призначає порт через змінну PORT, за замовчуванням 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Хендлер на команду /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Привіт! Я твій Telegram-бот, запущений на Render 24/7! 🚀")

async def main():
    # Запускаємо Flask у фоновому потоці, щоб він слухав пінги
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Запуск самого бота
    logging.info("Бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

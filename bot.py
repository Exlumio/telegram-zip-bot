import os
import asyncio
import logging
import nest_asyncio
import subprocess
from uuid import uuid4
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение токена и адреса вебхука из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Пример: https://your-bot-name.onrender.com

# Папка для сохранения временных файлов
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я зашифрую его в zip с паролем.")

# Обработка документов и медиафайлов
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file = message.document or message.audio or message.video or message.voice or message.photo[-1]

    tg_file = await file.get_file()
    file_id = str(uuid4())
    file_path = os.path.join(DOWNLOAD_DIR, file_id + "_input")
    output_path = os.path.join(DOWNLOAD_DIR, file_id + ".zip")

    # Скачиваем файл
    await tg_file.download_to_drive(file_path)

    # Генерируем пароль и шифруем
    password = uuid4().hex[:10]
    subprocess.run(["zip", "-j", "-P", password, output_path, file_path], check=True)

    # Отправка архива
    await message.reply_document(open(output_path, "rb"), caption=f"Пароль: `{password}`", parse_mode="Markdown")

    # Очистка
    os.remove(file_path)
    os.remove(output_path)

# Основная функция запуска бота
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.PHOTO | filters.AUDIO | filters.VIDEO | filters.VOICE,
        handle_file
    ))

    # Установка webhook
    await app.bot.delete_webhook()
    await app.bot.set_webhook(url=WEBHOOK_URL)

    # Запуск webhook-сервера
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())

import os
import logging
import asyncio
import zipfile
import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # например: https://your-bot-name.onrender.com

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я упакую его в zip с паролем!")

# Обработка файла
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    file = message.document or message.audio or message.video

    if not file:
        await message.reply_text("Файл не поддерживается.")
        return

    password = "secret123"
    file_name = file.file_name or "file"
    zip_name = file_name + ".zip"

    await message.reply_text("Скачиваю файл...")

    new_file = await file.get_file()
    async with aiohttp.ClientSession() as session:
        async with session.get(new_file.file_path) as resp:
            data = await resp.read()

    with open(file_name, "wb") as f:
        f.write(data)

    with zipfile.ZipFile(zip_name, 'w') as zipf:
        zipf.setpassword(password.encode())
        zipf.write(file_name)

    with open(zip_name, "rb") as f:
        await message.reply_document(f, filename=zip_name)

    os.remove(file_name)
    os.remove(zip_name)

# Основная функция
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.ATTACHMENT,
        handle_file
    ))

    # Запускаем webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

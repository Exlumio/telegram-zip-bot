import os
import logging
import asyncio
import aiohttp
import pyzipper
import secrets
import string
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

# Генератор случайного пароля
def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

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

    password = generate_password()
    file_name = file.file_name or "file"
    zip_name = file_name + ".zip"

    await message.reply_text("Скачиваю файл...")

    new_file = await file.get_file()
    async with aiohttp.ClientSession() as session:
        async with session.get(new_file.file_path) as resp:
            data = await resp.read()

    with open(file_name, "wb") as f:
        f.write(data)

    with pyzipper.AESZipFile(zip_name, 'w',
                             compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode('utf-8'))
        zf.write(file_name, arcname=file_name)

    with open(zip_name, "rb") as f:
        await message.reply_document(
            f,
            filename=zip_name,
            caption=f"✅ Архив создан.\n🔐 Пароль: `{password}`",
            parse_mode="Markdown"
        )

    os.remove(file_name)
    os.remove(zip_name)

# Основная функция
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_file))

    # Запускаем webhook
    await app.initialize()
    await app.start()
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        url_path="",
        webhook_url=WEBHOOK_URL,
    )

    logger.info("Bot started via webhook")
    await asyncio.Event().wait()  # Бесконечный цикл, чтобы бот жил

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

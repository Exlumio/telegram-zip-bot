import asyncio
import logging
import os
import random
import string
import subprocess

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import nest_asyncio
nest_asyncio.apply()

# Логгинг
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получи токен из переменной окружения (рекомендуется для Render)
TOKEN = os.environ.get("BOT_TOKEN")  # Установи в Render > Environment > BOT_TOKEN

# Генерация пароля
def generate_password(length=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я заархивирую его с паролем.")

# Обработка файла
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.video or update.message.audio
    if not file:
        await update.message.reply_text("Пожалуйста, пришли файл.")
        return

    file_id = file.file_id
    file_name = file.file_name
    password = generate_password()

    new_name = f"{file_id}_{file_name}"
    zip_name = f"{file_id}.zip"

    file_obj = await context.bot.get_file(file_id)
    await file_obj.download_to_drive(new_name)

    # Используем встроенный zip для создания архива с паролем (не AES)
    subprocess.run(["zip", "-P", password, zip_name, new_name], check=True)

    with open(zip_name, "rb") as f:
        await update.message.reply_document(f, filename=zip_name)

    await update.message.reply_text(f"🔐 Пароль: `{password}`", parse_mode="Markdown")

    # Удаляем временные файлы
    os.remove(new_name)
    os.remove(zip_name)

# Основной запуск
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Video.ALL | filters.Audio.ALL, handle_file))

    logger.info("Бот запущен...")
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()

# Запускаем с учётом nest_asyncio
asyncio.get_event_loop().create_task(main())
asyncio.get_event_loop().run_forever()

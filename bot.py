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

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://telegram-zip-bot.onrender.com"
PORT = int(os.environ.get("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# Генерация случайного пароля
def generate_password(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь мне файл, и я пришлю его в zip-архиве с паролем.")

# Обработка файлов
def zip_file_with_password(input_path, output_path, password):
    result = subprocess.run([
        'zip', '-j', '--password', password, output_path, input_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"ZIP error: {result.stderr}")
    return result.returncode == 0

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file:
        await update.message.reply_text("Отправь, пожалуйста, файл.")
        return

    file_path = f"downloads/{file.file_unique_id}_{file.file_name}"
    zip_path = file_path + ".zip"

    os.makedirs("downloads", exist_ok=True)

    telegram_file = await context.bot.get_file(file.file_id)
    await telegram_file.download_to_drive(file_path)

    password = generate_password()
    success = zip_file_with_password(file_path, zip_path, password)

    if success:
        await update.message.reply_document(
            document=open(zip_path, "rb"),
            filename=os.path.basename(zip_path),
            caption=f"Пароль для архива: {password}"
        )
    else:
        await update.message.reply_text("Не удалось создать архив.")

    os.remove(file_path)
    if os.path.exists(zip_path):
        os.remove(zip_path)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    await app.bot.set_webhook(url=WEBHOOK_URL)
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
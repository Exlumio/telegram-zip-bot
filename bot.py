import os
import logging
import nest_asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from aiohttp import web
import zipfile
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
BASE_DIR = "downloads"
nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я заархивирую его с паролем 🔐")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.audio
    if not file:
        await update.message.reply_text("Пожалуйста, пришли документ или аудиофайл.")
        return

    user_id = str(update.message.from_user.id)
    user_dir = os.path.join(BASE_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file.file_name)
    file_obj = await context.bot.get_file(file.file_id)
    await file_obj.download_to_drive(file_path)

    zip_path = os.path.join(user_dir, f"{file.file_name}.zip")
    password = datetime.now().strftime("%Y%m%d")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.setpassword(password.encode())
        zipf.write(file_path, arcname=file.file_name)

    with open(zip_path, "rb") as zf:
        await update.message.reply_document(zf, filename=os.path.basename(zip_path), caption=f"Пароль: `{password}`", parse_mode="Markdown")

    os.remove(file_path)
    os.remove(zip_path)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Audio.ALL, handle_file))

    # Устанавливаем Webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url="https://telegram-zip-bot.onrender.com",  # <== исправлено
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

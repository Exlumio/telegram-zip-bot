import os
import zipfile
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, MessageHandler, ContextTypes, CommandHandler, filters
)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например: https://telegram-zip-bot.onrender.com

# 📦 Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я заархивирую его для тебя.")

# 📦 Обработка полученных файлов
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = None
    if update.message.document:
        file = update.message.document
    elif update.message.audio:
        file = update.message.audio
    elif update.message.video:
        file = update.message.video

    if not file:
        await update.message.reply_text("Пришли файл — документ, аудио или видео.")
        return

    file_id = file.file_id
    new_file = await context.bot.get_file(file_id)
    file_path = f"downloads/{file.file_name}"
    zip_path = f"{file_path}.zip"

    os.makedirs("downloads", exist_ok=True)
    await new_file.download_to_drive(file_path)

    with zipfile.ZipFile(zip_path, "w") as zipf:
        zipf.write(file_path, arcname=file.file_name)

    await update.message.reply_document(document=open(zip_path, "rb"))

    os.remove(file_path)
    os.remove(zip_path)

# 🌐 Веб-сервер для Render
async def handle_webhook(request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return web.Response()

# 🚀 Основной запуск
async def main():
    global application
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(
        filters.DOCUMENT.ALL | filters.AUDIO | filters.VIDEO,
        handle_file
    ))

    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=WEBHOOK_URL)

    app = web.Application()
    app.router.add_post("/", handle_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)  # Render использует порт 10000
    await site.start()

    print("🚀 Bot is running via webhook...")

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())

import os
import asyncio
import tempfile
import string
import secrets
import subprocess

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web

TOKEN = os.getenv("TOKEN")
started_users = set()

def generate_password(length=8):
    alphabet = string.ascii_letters + string.digits
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in password) and any(c.isupper() for c in password) and any(c.isdigit() for c in password):
            return password

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in started_users:
        started_users.add(user_id)
        await update.message.reply_text("Привет! Пришли файл, и я заархивирую его с паролем.")
    else:
        await update.message.reply_text("Ты уже начал, можешь просто присылать файлы 😊")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in started_users:
        await update.message.reply_text("Сначала отправь команду /start.")
        return

    document = update.message.document
    if not document:
        await update.message.reply_text("Пожалуйста, пришли файл.")
        return

    password = generate_password()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, document.file_name)
        archive_path = os.path.join(tmpdir, f"{document.file_name}.zip")

        file = await document.get_file()
        await file.download_to_drive(input_path)

        subprocess.run([
            "zip", "-j", "-P", password, archive_path, input_path
        ], check=True)

        with open(archive_path, "rb") as f:
            await update.message.reply_document(f, filename=os.path.basename(archive_path))

        await update.message.reply_text(f"Файл заархивирован. Пароль: `{password}`", parse_mode="Markdown")

# Запуск aiohttp-заглушки + бота
async def run():
    # Бот
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    # aiohttp-заглушка
    web_app = web.Application()
    web_app.add_routes([web.get("/", lambda _: web.Response(text="Bot is alive"))])

    # Запуск бота и сервера параллельно
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

    print("HTTP server started. Telegram bot is polling...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(run())

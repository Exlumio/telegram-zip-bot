import os
import tempfile
import string
import secrets
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import asyncio

TOKEN = os.getenv("TOKEN")

# Хранилище пользователей, которые уже начали работу
started_users = set()

def generate_password(length=8):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password)):
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
        archive_path = os.path.join(tmpdir, document.file_name + ".zip")

        file = await document.get_file()
        await file.download_to_drive(input_path)

        # Архивируем через стандартный zip с паролем
        subprocess.run([
            "zip", "-P", password, archive_path, input_path
        ], check=True)

        with open(archive_path, "rb") as f:
            await update.message.reply_document(f, filename=os.path.basename(archive_path))

        await update.message.reply_text(f"Файл заархивирован. Пароль: `{password}`", parse_mode="Markdown")

# HTTP-заглушка для Render (чтобы не падал от отсутствия порта)
async def handle(request):
    return web.Response(text="Bot is running!")

async def run_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    # Запуск Telegram-бота и aiohttp-сервера одновременно
    loop = asyncio.get_event_loop()
    loop.create_task(run_web_server())
    loop.run_until_complete(app.run_polling())

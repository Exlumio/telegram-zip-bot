import os
import tempfile
import pyminizip
import string
import secrets
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

def generate_password(length=8):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password) and sum(c.isdigit() for c in password) >= 1):
            return password

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я заархивирую его с паролем.")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document:
        await update.message.reply_text("Пожалуйста, пришли файл.")
        return

    password = generate_password()

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, document.file_name)
        archive_path = os.path.join(tmpdir, document.file_name + ".zip")

        file = await document.get_file()
        await file.download_to_drive(file_path)

        pyminizip.compress(file_path, None, archive_path, password, 5)

        with open(archive_path, "rb") as f:
            await update.message.reply_document(document=f, filename=os.path.basename(archive_path))

        await update.message.reply_text(f"Файл заархивирован. Пароль: `{password}`", parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.run_polling()

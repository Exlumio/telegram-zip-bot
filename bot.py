import os
import asyncio
import logging
import secrets
import string
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)
import nest_asyncio

# Логгирование
logging.basicConfig(level=logging.INFO)

# Токен из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

# Генерация случайного пароля
def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл, и я отправлю его в ZIP-архиве с паролем.")

# Обработка файлов
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document or update.message.video or update.message.audio
    if not file:
        await update.message.reply_text("Не удалось определить тип файла.")
        return

    # Скачиваем файл
    file_path = f"{file.file_unique_id}_{file.file_name}"
    new_file = await file.get_file()
    await new_file.download_to_drive(file_path)

    # Генерируем пароль и имя архива
    password = generate_password()
    zip_name = file_path + ".zip"

    # Используем встроенный zip (Render поддерживает)
    zip_command = ["zip", "-j", "-P", password, zip_name, file_path]
    subprocess.run(zip_command)

    # Отправка архива пользователю
    with open(zip_name, "rb") as archive:
        await update.message.reply_document(archive, filename=zip_name)

    # Отправка пароля
    await update.message.reply_text(f"🔐 Пароль от архива: `{password}`", parse_mode="Markdown")

    # Удаляем временные файлы
    os.remove(file_path)
    os.remove(zip_name)

# Основной запуск
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ATTACHMENT, handle_file))

    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())

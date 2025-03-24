import os
import subprocess
import tempfile
import logging
import secrets
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Отправь мне файл, и я пришлю его в zip-архиве с паролем.")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    document = update.message.document or update.message.video or update.message.audio
    if not document:
        await update.message.reply_text("Пожалуйста, отправь файл.")
        return

    file = await context.bot.get_file(document.file_id)

    # Сохраняем оригинальный файл во временную папку
    with tempfile.TemporaryDirectory() as tmpdir:
        original_path = os.path.join(tmpdir, document.file_name)
        zip_path = os.path.join(tmpdir, f"{document.file_name}.zip")
        password = secrets.token_hex(4)

        await file.download_to_drive(original_path)

        # Создание zip-архива с паролем через встроенную утилиту zip
        result = subprocess.run(
            ["zip", "-j", "-P", password, zip_path, original_path],
            capture_output=True,
        )

        if result.returncode != 0:
            logger.error(f"Ошибка при создании архива: {result.stderr.decode()}")
            await update.message.reply_text("Произошла ошибка при создании архива.")
            return

        # Отправляем zip-файл обратно пользователю
        with open(zip_path, "rb") as f:
            await update.message.reply_document(f, filename=f"{document.file_name}.zip")

        await update.message.reply_text(f"Пароль для архива: `{password}`", parse_mode="Markdown")


async def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("Переменная окружения BOT_TOKEN не установлена")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.Document.ALL | filters.Video | filters.Audio.ALL, handle_file))

    logging.info("Bot started.")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

import os
import logging
import asyncio
import aiohttp
import pyzipper
import secrets
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # например: https://your-bot-name.onrender.com
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

# Хранилище режимов (в памяти, позже можно заменить на базу)
user_modes = {}  # user_id: 'zip' или 'ai'

# Генератор случайного пароля
def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Клавиатура для выбора режима
def mode_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udce6 Архиватор", callback_data="mode_zip"),
         InlineKeyboardButton("\ud83e\udde0 Нейросеть", callback_data="mode_ai")]
    ])

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = 'zip'  # По умолчанию архиватор
    await update.message.reply_text(
        "Привет! Выберите режим работы:",
        reply_markup=mode_keyboard()
    )

# Обработка выбора режима
async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "mode_zip":
        user_modes[user_id] = 'zip'
        await query.edit_message_text("Режим установлен: \ud83d\udce6 Архиватор")
    elif query.data == "mode_ai":
        user_modes[user_id] = 'ai'
        await query.edit_message_text("Режим установлен: \ud83e\udde0 Нейросеть")

# Обработка файлов
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = user_modes.get(user_id, 'zip')

    if mode == 'zip':
        await handle_zip_file(update, context)
    elif mode == 'ai':
        await handle_ai_message(update, context)

# Обработка архивации файла
async def handle_zip_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            caption=f"\u2705 Архив создан.\n\ud83d\udd10 Пароль: `{password}`",
            parse_mode="Markdown"
        )

    os.remove(file_name)
    os.remove(zip_name)

# Обработка текстов для нейросети
async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.caption or update.message.text
    if not prompt:
        await update.message.reply_text("Пожалуйста, отправьте текст или файл с описанием.")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    await update.message.reply_chat_action(action="typing")

    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers) as resp:
            if resp.status != 200:
                await update.message.reply_text("Ошибка при обращении к нейросети. Попробуйте позже.")
                return

            result = await resp.json()
            reply = result["choices"][0]["message"]["content"]
            await update.message.reply_text(reply)

# Основная функция
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_mode))
    app.add_handler(MessageHandler(filters.ATTACHMENT | filters.TEXT, handle_file))

    # Запускаем webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", "10000")),
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
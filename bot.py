import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! İngilizce kelime yazabilirsin 🙂")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    try:
        response = requests.get(url, timeout=10)
    except Exception:
        await update.message.reply_text("API bağlantı hatası.")
        return

    if response.status_code != 200:
        await update.message.reply_text("Kelime bulunamadı.")
        return

    try:
        data = response.json()
        meaning = data[0]["meanings"][0]["definitions"][0]["definition"]
    except Exception:
        await update.message.reply_text("Anlam alınamadı.")
        return

    await update.message.reply_text(f"{word}:\n{meaning}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()

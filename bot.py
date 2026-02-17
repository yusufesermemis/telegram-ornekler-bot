import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! İngilizce kelime yaz.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.lower()

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text("Kelime bulunamadı.")
        return

    data = response.json()
    meaning = data[0]["meanings"][0]["definitions"][0]["definition"]

    await update.message.reply_text(f"{word}:\n{meaning}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot çalışıyor...")
    app.run_polling()

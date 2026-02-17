from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests

TOKEN = "8251344959:AAEysGNvCUfXD2D9xB-0_K7PndBxpIPNsHg"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    word = update.message.text.lower()

    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(url)

    if response.status_code != 200:
        await update.message.reply_text("Kelime bulunamadı.")
        return

    data = response.json()
    meaning = data[0]['meanings'][0]['definitions'][0]['definition']

    await update.message.reply_text(f"{word}:\n{meaning}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("Bot çalışıyor...")
app.run_polling()

import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator  # <-- YENİ EKLENEN KISIM

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Bir İngilizce kelime yaz, hem tanımını hem Türkçesini getireyim. 🇹🇷🇬🇧")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # Kullanıcıya "yazıyor..." bilgisi gönderelim
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 1. İNGİLİZCE TANIM (Mevcut API)
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    english_def = "Tanım bulunamadı."
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            english_def = data[0]["meanings"][0]["definitions"][0]["definition"]
    except Exception:
        english_def = "Bağlantı hatası."

    # 2. TÜRKÇE ÇEVİRİ (Yeni Özellik)
    try:
        # Kelimeyi Türkçe'ye çeviriyoruz
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(word)
    except Exception:
        turkish_meaning = "Çeviri yapılamadı."

    # 3. SONUCU BİRLEŞTİRİP GÖNDERME
    reply_text = (
        f"🔤 **Kelime:** {word.capitalize()}\n\n"
        f"🇹🇷 **Türkçesi:** {turkish_meaning.capitalize()}\n"
        f"🇬🇧 **İngilizce Tanımı:** {english_def}"
    )

    await update.message.reply_text(reply_text, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
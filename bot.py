import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user_name}! 👋\nKelimeyi yaz, neyi görmek istediğini butonlardan seç.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # Başlığı sade tutuyoruz, otomatik karşılık yazmıyor
    header_text = f"🔎 **Kelime:** {word.capitalize()}"

    # Butonlar: Artık her zaman 3 buton da çıkıyor
    keyboard = [
        [InlineKeyboardButton("🔄 Çeviri / Karşılık", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")],
        [InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{header_text}\nLütfen bir işlem seçin:", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    data = query.data.split("|")
    action = data[0]
    word = data[1]

    result_content = ""

    # Karar mekanizması için çevirileri hazırla
    try:
        en_res = GoogleTranslator(source='auto', target='en').translate(word).lower()
        tr_res = GoogleTranslator(source='auto', target='tr').translate(word).lower()
    except:
        en_res, tr_res = word, word

    if action == "ceviri":
        # Eğer kullanıcı zaten Türkçe yazdıysa İngilizcesini göster, yoksa Türkçesini
        if word == tr_res:
            result_content = f"🇬🇧 **İngilizce Karşılığı:** {en_res.capitalize()}"
        else:
            result_content = f"🇹🇷 **Türkçe Anlamı:** {tr_res.capitalize()}"

    elif action == "tanim":
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{en_res}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                definition = response.json()[0]["meanings"][0]["definitions"][0]["definition"]
                result_content = f"📖 **İngilizce Tanım:** {definition}"
            else:
                result_content = "Tanım bulunamadı."
        except:
            result_content = "Bağlantı hatası."

    elif action == "esanlam":
        try:
            url = f"https://api.datamuse.com/words?rel_syn={en_res}"
            response = requests.get(url, timeout=5)
            items = [item['word'] for item in response.json()[:5]]
            synonyms = ", ".join(items) if items else "Bulunamadı"
            result_content = f"🔥 **Eş Anlamlılar:** _{synonyms}_"
        except:
            result_content = "Veri hatası."

    # Mesajı güncelle
    keyboard = [
        [InlineKeyboardButton("🔄 Çeviri / Karşılık", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")],
        [InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"🔎 **Kelime:** {word.capitalize()}\n\n{result_content}", 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
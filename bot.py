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
    await update.message.reply_text(f"Merhaba {user_name}! 👋\nKelimeyi yaz, anlamını öğren ve cümle içinde nasıl kullanıldığını gör. 📝")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    header_text = f"🔎 **Kelime:** {word.capitalize()}"

    # Butonlar: Favori yerine Örnek Cümle eklendi
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("📝 Örnek Cümleler", callback_data=f"örnek|{word}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"{header_text}\nLütfen bir işlem seçin:", reply_markup=reply_markup, parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("|")
    action, word = data[0], data[1]

    result_content = ""

    # Karar mekanizması için çevirileri hazırla
    try:
        en_res = GoogleTranslator(source='auto', target='en').translate(word).lower()
        tr_res = GoogleTranslator(source='auto', target='tr').translate(word).lower()
    except:
        en_res, tr_res = word, word

    # --- API İŞLEMLERİ ---
    if action == "ceviri":
        result_content = f"🇬🇧 **İngilizce:** {en_res.capitalize()}" if word == tr_res else f"🇹🇷 **Türkçe:** {tr_res.capitalize()}"
    
    elif action == "tanim" or action == "örnek":
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{en_res}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()[0]
                if action == "tanim":
                    definition = data['meanings'][0]['definitions'][0]['definition']
                    result_content = f"📖 **Tanım:** {definition}"
                else: # Örnek Cümle aksiyonu
                    # API'den örnek cümleyi bulmaya çalışıyoruz
                    example = "Bu kelime için uygun bir örnek cümle bulunamadı."
                    for meaning in data.get('meanings', []):
                        for definition in meaning.get('definitions', []):
                            if definition.get('example'):
                                example = definition['example']
                                break
                        if example != "Bu kelime için uygun bir örnek cümle bulunamadı.": break
                    
                    result_content = f"📝 **Örnek Cümle:**\n_{example.capitalize()}_"
            else:
                result_content = "Bilgi bulunamadı."
        except: result_content = "Bağlantı hatası."

    elif action == "esanlam":
        try:
            url = f"https://api.datamuse.com/words?rel_syn={en_res}"
            res = requests.get(url, timeout=5)
            items = [item['word'] for item in res.json()[:5]]
            result_content = f"🔗 **Eş Anlamlılar:** _{', '.join(items)}_" if items else "Bulunamadı."
        except: result_content = "Hata oluştu."

    # Klavye düzenini koru
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("📝 Örnek Cümleler", callback_data=f"örnek|{word}")]
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
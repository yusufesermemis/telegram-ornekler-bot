import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- ÖZEL ÇEVİRİ FONKSİYONU (MyMemory API #10) ---
def translate_word(text, source_lang, target_lang):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_lang}|{target_lang}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()["responseData"]["translatedText"].lower()
    except:
        return text
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user_name}! 👋\nArtık çok daha güçlü bir çeviri motoru kullanıyorum. 🚀")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    header_text = f"🔎 **Kelime:** {word.capitalize()}"

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}"),
         InlineKeyboardButton("🔊 Sesli Dinle", callback_data=f"ses|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("📝 Örnek Cümleler", callback_data=f"örnek|{word}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"{header_text}\nLütfen bir işlem seçin:", reply_markup=reply_markup, parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, word = data[0], data[1]

    if action == "ses":
        await query.answer("Ses hazırlanıyor... 🎧")
        # Ses için her zaman İngilizce karşılığını bulalım
        en_word = translate_word(word, "tr", "en")
        tts = gTTS(text=en_word, lang='en')
        file_name = f"{word}.mp3"
        tts.save(file_name)
        with open(file_name, 'rb') as audio:
            await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio)
        os.remove(file_name)
        return

    await query.answer()
    result_content = ""

    # --- AKILLI ÇEVİRİ MANTIĞI ---
    # Hem Türkçesini hem İngilizcesini çekiyoruz (Garantici yöntem)
    tr_to_en = translate_word(word, "tr", "en")
    en_to_tr = translate_word(word, "en", "tr")

    if action == "ceviri":
        # Eğer kelime Türkçeyse İngilizcesini, İngilizceyse Türkçesini göster
        if word == en_to_tr: # Kelime İngilizce ise
            result_content = f"🇹🇷 **Türkçe Anlamı:** {en_to_tr.capitalize()}"
        else: # Kelime Türkçe ise
            result_content = f"🇬🇧 **İngilizce Karşılığı:** {tr_to_en.capitalize()}"

    elif action == "tanim" or action == "örnek":
        # Tanım ve örnek için mutlaka İngilizce kelime lazım
        search_word = tr_to_en if word != tr_to_en else word
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()[0]
                if action == "tanim":
                    result_content = f"📖 **Tanım:** {data['meanings'][0]['definitions'][0]['definition']}"
                else:
                    example = "Örnek bulunamadı."
                    for m in data.get('meanings', []):
                        for d in m.get('definitions', []):
                            if d.get('example'): example = d['example']; break
                    result_content = f"📝 **Örnek Cümle:**\n_{example.capitalize()}_"
            else: result_content = "Bilgi bulunamadı."
        except: result_content = "Bağlantı hatası."

    elif action == "esanlam":
        search_word = tr_to_en if word != tr_to_en else word
        try:
            url = f"https://api.datamuse.com/words?rel_syn={search_word}"
            res = requests.get(url, timeout=5)
            items = [item['word'] for item in res.json()[:5]]
            result_content = f"🔗 **Eş Anlamlılar:** _{', '.join(items)}_" if items else "Bulunamadı."
        except: result_content = "Hata oluştu."

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}"),
         InlineKeyboardButton("🔊 Sesli Dinle", callback_data=f"ses|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("📝 Örnek Cümleler", callback_data=f"örnek|{word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"🔎 **Kelime:** {word.capitalize()}\n\n{result_content}", reply_markup=reply_markup, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
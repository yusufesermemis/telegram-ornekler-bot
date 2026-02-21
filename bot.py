import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Merhaba! 👋\nArtık kelimelerin **tüm anlamlarını** detaylıca görebilirsin.\n\n"
        "Bir kelime yaz ve farkı gör! 👇", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Tüm Anlamlar", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Detaylı Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek Cümle", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{word}")]
    ]
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Öğrenmek istediğin özelliği seç:_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    await query.answer()

    en_to_tr = get_translation(val, "en", "tr")
    tr_to_en = get_translation(val, "tr", "en")
    
    header = f"🔎 **Kelime:** `{val.capitalize()}`\n"
    content = ""

    # --- ÇOKLU ANLAM MANTIĞI ---
    if action == "c":
        search_word = val if en_to_tr != val else tr_to_en
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
            if r.status_code == 200:
                data = r.json()[0]
                meanings_list = []
                for m in data['meanings']:
                    part_of_speech = m['partOfSpeech'] # Noun, Verb vb.
                    # MyMemory ile her bir temel tanımı Türkçeye çevirelim
                    definition = m['definitions'][0]['definition']
                    tr_def = get_translation(definition, "en", "tr")
                    meanings_list.append(f"📍 *{part_of_speech.capitalize()}:* {tr_def}")
                
                content = "📚 **Farklı Anlamları**\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(meanings_list)
            else:
                # API'de yoksa MyMemory'den tek anlamı ver
                res = en_to_tr if en_to_tr != val else tr_to_en
                content = f"✨ **Karşılığı:** `{res.capitalize()}`"
        except:
            content = "🚫 Bir hata oluştu."

    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    elif action in ["t", "o", "e"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [f"`{i['word']}`" for i in r.json()[:5]]
                content = "🔗 **Eş Anlamlılar**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        content = f"📖 **Tanım:** _{defi}_"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        content = f"📝 **Örnek:** _“{ex}”_"
                else: content = "🚫 Bilgi bulunamadı."
        except: content = "🚫 Bağlantı hatası."

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Tüm Anlamlar", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Detaylı Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek Cümle", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{val}")]
    ]
    
    await query.edit_message_text(text=header + content, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
import os
import requests
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- DEĞİŞKEN İSMİNİ BURADA EŞİTLEDİK ---
# Railway'deki isminle (GEMINI_API_KEY) tam olarak aynı yaptık.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

model = None

# --- YAPAY ZEKA AYARLARI ---
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # En güncel ve hızlı model
        model = genai.GenerativeModel('gemini-1.5-flash')
        logging.info("✅ Gemini AI bağlantısı Railway anahtarı ile başarılı.")
    except Exception as e:
        logging.error(f"⚠️ Google AI Hatası: {e}")
else:
    logging.warning("⚠️ Railway'de GEMINI_API_KEY bulunamadı!")

# --- MyMemory Çeviri ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

# --- AI DEYİM BULUCU ---
async def fetch_idioms_with_ai(word):
    if not model:
        return ["⚠️ AI Modeli hazır değil. Lütfen Railway ayarlarını kontrol edin."]
    
    try:
        prompt = (
            f"List 3 popular English idioms containing the word '{word}'. "
            "Format exactly like this example:\n"
            "Piece of cake - Çocuk oyuncağı\n"
            "Do not allow extra text, just the list."
        )
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        formatted_idioms = []
        for line in text.split('\n'):
            if "-" in line:
                parts = line.split("-")
                eng = parts[0].strip()
                tr = parts[1].strip() if len(parts) > 1 else ""
                formatted_idioms.append(f"🔹 *{eng}*\n    _{tr}_")
        
        return formatted_idioms if formatted_idioms else ["Bu kelimeyle ilgili yaygın bir deyim bulunamadı."]
    except Exception as e:
        return [f"⚠️ Bağlantı hatası: {str(e)}"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    msg = (
        f"Merhaba {user}! 👋\n\n"
        "Yapay zeka destekli asistanın hazır! 🧠\n"
        "İstediğin kelimeyi yaz, deyimleri senin için canlı bulayım.\n\n"
        "_Kelime yazarak başla_ 👇"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{word}"),
         InlineKeyboardButton("🎭 Deyimler (AI)", callback_data=f"i|{word}")]
    ]
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Ne öğrenmek istersin?_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    
    if action == "i":
        await query.answer("🤖 Yapay zeka araştırıyor...")
    else:
        await query.answer()

    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")
    
    header = f"🔎 **Kelime:** `{val.capitalize()}`\n"
    result_text = ""

    if action == "c":
        if en_to_tr != val: 
            result_text = f"🇹🇷 **Türkçe Anlamı**\n━━━━━━━━━━━━━━━━━━\n✨ `{en_to_tr.capitalize()}`"
        else:
            result_text = f"🇬🇧 **İngilizce Karşılığı**\n━━━━━━━━━━━━━━━━━━\n✨ `{tr_to_en.capitalize()}`"

    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    elif action == "i":
        search_word = val if en_to_tr != val else tr_to_en
        idioms = await fetch_idioms_with_ai(search_word)
        result_text = "🎭 **İlgili Deyimler (AI)**\n━━━━━━━━━━━━━━━━━━\n" + "\n\n".join(idioms)

    elif action in ["t", "o", "e"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [f"`{i['word'].capitalize()}`" for i in r.json()[:5]]
                result_text = "🔗 **Eş Anlamlı Kelimeler**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        result_text = f"📖 **İngilizce Tanım**\n━━━━━━━━━━━━━━━━━━\n_{defi}_"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        result_text = f"📝 **Örnek Cümle**\n━━━━━━━━━━━━━━━━━━\n_“{ex}”_"
                else: result_text = "🚫 _Bilgi bulunamadı._"
        except: result_text = "🚫 _Bağlantı hatası._"

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}"),
         InlineKeyboardButton("🎭 Deyimler (AI)", callback_data=f"i|{val}")]
    ]
    
    await query.edit_message_text(text=header + result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
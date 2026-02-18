import os
import requests
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# --- YAPAY ZEKA AYARLARI (GÜNCELLENDİ) ---
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    # ESKİ: model = genai.GenerativeModel('gemini-pro')
    # YENİ: Model ismini 'gemini-1.5-flash' yaptık. Hem daha hızlı hem de ücretsiz kotaya uygun.
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    logging.warning("⚠️ GEMINI_API_KEY bulunamadı! Deyim özelliği çalışmayabilir.")

# --- MyMemory Çeviri ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

# --- AI DEYİM BULUCU ---
async def fetch_idioms_with_ai(word):
    if not GEMINI_KEY:
        return ["⚠️ API Anahtarı eksik."]
    
    try:
        # Yapay zekaya net komut veriyoruz
        prompt = (
            f"List 3 popular English idioms containing the word '{word}'. "
            "Format exactly like this example:\n"
            "Piece of cake - Çocuk oyuncağı\n"
            "Do not allow extra text, just the list."
        )
        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        
        # Gelen cevabı listeye çevirip süsleyelim
        formatted_idioms = []
        for line in text.split('\n'):
            if "-" in line:
                parts = line.split("-")
                eng = parts[0].strip()
                tr = parts[1].strip()
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
    if not update.message.text: return
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
    content = ""

    # 1. CEVIRI
    if action == "c":
        if en_to_tr != val: 
            content = f"🇹🇷 **Türkçe Anlamı**\n━━━━━━━━━━━━━━━━━━\n✨ `{en_to_tr.capitalize()}`"
        else:
            content = f"🇬🇧 **İngilizce Karşılığı**\n━━━━━━━━━━━━━━━━━━\n✨ `{tr_to_en.capitalize()}`"

    # 2. SES
    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # 3. DEYIMLER (YAPAY ZEKA)
    elif action == "i":
        search_word = val if en_to_tr != val else tr_to_en
        idioms = await fetch_idioms_with_ai(search_word)
        content = "🎭 **İlgili Deyimler (AI)**\n━━━━━━━━━━━━━━━━━━\n" + "\n\n".join(idioms)

    # 4. TANIM / ORNEK / ES ANLAM
    elif action in ["t", "o", "e"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [f"`{i['word'].capitalize()}`" for i in r.json()[:5]]
                content = "🔗 **Eş Anlamlı Kelimeler**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        content = f"📖 **İngilizce Tanım**\n━━━━━━━━━━━━━━━━━━\n_{defi}_"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        content = f"📝 **Örnek Cümle**\n━━━━━━━━━━━━━━━━━━\n_“{ex}”_"
                else: content = "🚫 _Bilgi bulunamadı._"
        except: content = "🚫 _Bağlantı hatası._"

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}"),
         InlineKeyboardButton("🎭 Deyimler (AI)", callback_data=f"i|{val}")]
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
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
# Railway'deki değişken isminle aynı olmalı
GEMINI_KEY = os.getenv("GEMINI_API_KEY") 

# --- ÇEVİRİ FONKSİYONU ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

# --- DOĞRUDAN GOOGLE API BAĞLANTISI (KÜTÜPHANESİZ) ---
async def fetch_dynamic_idioms(word):
    if not GEMINI_KEY:
        return "⚠️ Railway'de GEMINI_API_KEY bulunamadı."
    
    # Gemini 1.5 Flash API'sine doğrudan istek atıyoruz
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    # Yapay zekaya kesin bir format emri veriyoruz
    prompt = (
        f"Bana içinde '{word}' kelimesi geçen 2 İngilizce deyim (idiom) ve 1 İngilizce atasözü (proverb) bul. "
        "Format kesinlikle şu şekilde olmalı:\n"
        "🔹 *İngilizce Deyim/Atasözü*\n"
        "    _Türkçe anlamı_\n\n"
        "Başka hiçbir açıklama veya giriş cümlesi yazma, sadece bu formatta 3 madde ver."
    )
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            # Yapay zekanın ürettiği metni alıyoruz
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            return "🎭 **Deyimler ve Atasözleri (AI)**\n━━━━━━━━━━━━━━━━━━\n" + text
        else:
            return f"⚠️ API Hatası: {response.status_code} - Model yanıt vermedi."
    except Exception as e:
        return f"⚠️ Bağlantı hatası: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"Merhaba {user}! 👋\nArtık kelimelerin tüm anlamlarını görebilir ve yapay zekadan o an canlı deyimler/atasözleri üretebilirsin.\n\n"
        "Hadi kelime yazarak başla! 👇", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Tüm Anlamlar", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🎭 Deyimler & Atasözleri", callback_data=f"i|{word}")]
    ]
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Öğrenmek istediğin özelliği seç:_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    
    if action == "i":
        await query.answer("🤖 Yapay zeka senin için düşünüyor...")
    else:
        await query.answer()

    en_to_tr = get_translation(val, "en", "tr")
    tr_to_en = get_translation(val, "tr", "en")
    
    header = f"🔎 **Kelime:** `{val.capitalize()}`\n"
    content = ""

    # --- TÜM ANLAMLAR ---
    if action == "c":
        search_word = val if en_to_tr != val else tr_to_en
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
            if r.status_code == 200:
                data_api = r.json()[0]
                meanings_list = []
                for m in data_api['meanings']:
                    part = m['partOfSpeech']
                    definition = m['definitions'][0]['definition']
                    tr_def = get_translation(definition, "en", "tr")
                    meanings_list.append(f"📍 *{part.capitalize()}:* {tr_def}")
                content = "📚 **Farklı Anlamları**\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(meanings_list)
            else:
                res = en_to_tr if en_to_tr != val else tr_to_en
                content = f"✨ **Karşılığı:** `{res.capitalize()}`"
        except: content = "🚫 Bir hata oluştu."

    # --- YAPAY ZEKA DEYİM & ATASÖZÜ (DİNAMİK) ---
    elif action == "i":
        search_word = val if en_to_tr != val else tr_to_en
        content = await fetch_dynamic_idioms(search_word)

    # --- SES DOSYASI ---
    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # --- TANIM & ÖRNEK ---
    elif action in ["t", "o"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
            if r.status_code == 200:
                d = r.json()[0]
                if action == "t":
                    content = f"📖 **Tanım:** _{d['meanings'][0]['definitions'][0]['definition']}_"
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
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🎭 Deyimler & Atasözleri", callback_data=f"i|{val}")]
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
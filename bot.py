import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN", "").strip()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip() 

# --- ÇEVİRİ FONKSİYONU (Sadece ses ve arama altyapısı için) ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

# --- AKILLI GOOGLE API BAĞLANTISI (Sadece Anlamlar ve Deyimler İçin) ---
async def fetch_from_gemini(prompt):
    if not GEMINI_KEY:
        return "⚠️ Railway'de GEMINI_API_KEY bulunamadı veya boş."
    
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
        r_list = requests.get(list_url, timeout=10)
        
        if r_list.status_code != 200:
            return f"⚠️ API Anahtarı Hatası: {r_list.status_code}"
            
        models = r_list.json().get('models', [])
        chosen_model = None
        
        for m in models:
            if 'gemini-1.5-flash' in m['name'] and 'generateContent' in m.get('supportedGenerationMethods', []):
                chosen_model = m['name']
                break
                
        if not chosen_model:
            for m in models:
                if 'gemini' in m['name'] and 'generateContent' in m.get('supportedGenerationMethods', []):
                    chosen_model = m['name']
                    break
                    
        if not chosen_model:
            return "⚠️ Uygun bir model bulunamadı."

        url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={GEMINI_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            error_msg = response.json().get('error', {}).get('message', 'Bilinmeyen API hatası')
            return f"⚠️ API Hatası ({response.status_code}): {error_msg}"
            
    except Exception as e:
        return f"⚠️ Bağlantı hatası: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"Merhaba {user}! 👋\nArtık kelimelerin tüm anlamlarını görebilir, eş anlamlılarını bulabilir ve yapay zekadan o an canlı deyimler üretebilirsin.\n\n"
        "Hadi kelime yazarak başla! 👇", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Tüm Anlamlar", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{word}"),
         InlineKeyboardButton("🎭 Deyimler (AI)", callback_data=f"i|{word}")]
    ]
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Öğrenmek istediğin özelliği seç:_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    
    if action in ["i", "c"]:
        await query.answer("🤖 Aranıyor...")
    else:
        await query.answer()

    en_to_tr = get_translation(val, "en", "tr")
    tr_to_en = get_translation(val, "tr", "en")
    
    header = f"🔎 **Kelime:** `{val.capitalize()}`\n"
    content = ""

    # --- 1. TÜM ANLAMLAR (TURENG STİLİ KELİME LİSTESİ) ---
    if action == "c":
        prompt = (f"'{val}' kelimesinin sözlükteki en yaygın 4 veya 5 karşılığını listele. "
                  f"Hiçbir uzun açıklama veya cümle kurma. Tıpkı Tureng sözlükteki gibi sadece kelimeleri alt alta şu formatta yaz:\n"
                  f"🔹 Anlam 1\n🔹 Anlam 2\n🔹 Anlam 3")
        ans = await fetch_from_gemini(prompt)
        content = "📚 **Farklı Anlamları**\n━━━━━━━━━━━━━━━━━━\n" + ans

    # --- 2. YAPAY ZEKA DEYİM & ATASÖZÜ ---
    elif action == "i":
        prompt = (f"Bana içinde '{val}' kelimesi geçen 2 İngilizce deyim (idiom) ve 1 İngilizce atasözü (proverb) bul. "
                  "Format kesinlikle şu şekilde olmalı:\n"
                  "🔹 *İngilizce Deyim/Atasözü*\n"
                  "    _Türkçe anlamı_\n\n"
                  "Başka hiçbir açıklama veya giriş cümlesi yazma, sadece bu formatta 3 madde ver.")
        ans = await fetch_from_gemini(prompt)
        content = "🎭 **Deyimler ve Atasözleri (AI)**\n━━━━━━━━━━━━━━━━━━\n" + ans

    # --- 3. EŞ ANLAMLILAR (Orjinal Kod) ---
    elif action == "e":
        search_word = val if en_to_tr != val else tr_to_en
        try:
            r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
            items = [f"`{i['word'].capitalize()}`" for i in r.json()[:5]]
            content = "🔗 **Eş Anlamlı Kelimeler**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
        except: content = "🚫 Bağlantı hatası."

    # --- 4. SES DOSYASI (Orjinal Kod) ---
    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # --- 5. TANIM & ÖRNEK (Orjinal Kod - DictionaryAPI) ---
    elif action in ["t", "o"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
            if r.status_code == 200:
                d = r.json()[0]
                if action == "t":
                    content = f"📖 **İngilizce Tanım:** _{d['meanings'][0]['definitions'][0]['definition']}_"
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
        [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{val}"),
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
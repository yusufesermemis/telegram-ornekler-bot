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

# --- TEK BİR MERKEZİ YAPAY ZEKA FONKSİYONU ---
async def ask_gemini(prompt):
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

# --- SES İÇİN BASİT ÇEVİRİ (Sadece TTS için kullanacağız) ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"Merhaba {user}! 👋\nBotun artık %100 Yapay Zeka gücüyle çalışıyor. Kelimeleri bağlamına göre anlar ve asla saçmalamaz!\n\n"
        "Hadi kelime yazarak başla! 👇", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri & Anlamlar", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{word}"),
         InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{word}")]
    ]
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Öğrenmek istediğin özelliği seç:_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    
    if action != "s":
        await query.answer("🤖 Asistan düşünüyor...")
    else:
        await query.answer()

    header = f"🔎 **Kelime:** `{val.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n"
    content = ""

    # --- 1. TÜM ANLAMLAR VE ÇEVİRİ ---
    if action == "c":
        prompt = (f"Bana '{val}' kelimesinin net bir çevirisini yap. "
                  f"Ardından isim, fiil veya sıfat gibi farklı kullanımları varsa maddeler halinde kısaca Türkçe açıkla. "
                  f"Formatı temiz tut, giriş cümlesi yazma.")
        content = "📚 **Farklı Anlamları**\n" + await ask_gemini(prompt)

    # --- 2. TANIM ---
    elif action == "t":
        prompt = (f"Bana '{val}' kelimesinin ne anlama geldiğini açıklayan net ve kısa bir sözlük tanımı yap. "
                  f"Eğer verilen kelime Türkçe ise, önce İngilizce karşılığını söyle, sonra o İngilizce kelimenin tanımını Türkçe olarak yap. "
                  f"Giriş cümlesi yazma.")
        content = "📖 **Tanım**\n" + await ask_gemini(prompt)

    # --- 3. ÖRNEK CÜMLE ---
    elif action == "o":
        prompt = (f"İçinde '{val}' geçen 2 tane örnek cümle kur ve altlarına Türkçe çevirilerini yaz. "
                  f"Eğer kelime Türkçe ise, o kelimenin İngilizce karşılığını kullanarak İngilizce örnek cümleler kur. "
                  f"Giriş cümlesi yazma.")
        content = "📝 **Örnek Cümleler**\n" + await ask_gemini(prompt)

    # --- 4. EŞ ANLAMLILAR ---
    elif action == "e":
        prompt = (f"'{val}' kelimesinin en yaygın 3 eş anlamlısını (synonym) listele ve yanlarına Türkçe anlamlarını ekle. "
                  f"Giriş cümlesi yazma.")
        content = "🔗 **Eş Anlamlılar**\n" + await ask_gemini(prompt)

    # --- 5. DEYİMLER ---
    elif action == "i":
        prompt = (f"Bana içinde '{val}' kelimesi geçen 2 İngilizce deyim (idiom) ve 1 İngilizce atasözü (proverb) bul. "
                  f"Format: 🔹 *Deyim/Atasözü* - _Türkçe anlamı_. Başka hiçbir metin yazma.")
        content = "🎭 **Deyimler ve Atasözleri**\n" + await ask_gemini(prompt)

    # --- 6. SES DİNLEME (Değişmedi) ---
    elif action == "s":
        en_to_tr = get_translation(val, "en", "tr")
        tr_to_en = get_translation(val, "tr", "en")
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # Sadece metin içeriği değişen butonlar için mesajı güncelle
    if action != "s":
        keyboard = [
            [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri & Anlamlar", callback_data=f"c|{val}"),
             InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
            [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
             InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
            [InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"e|{val}"),
             InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{val}")]
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
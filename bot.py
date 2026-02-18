import os
import requests
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- QUİZ VERİ SETİ (Örnek Sorular) ---
QUIZ_QUESTIONS = [
    {"q": "Apple", "a": "Elma", "options": ["Armut", "Elma", "Kiraz", "Muz"]},
    {"q": "Success", "a": "Başarı", "options": ["Başarı", "Hata", "Örnek", "Sabır"]},
    {"q": "Wonderful", "a": "Harika", "options": ["Kötü", "Sıradan", "Harika", "Sıkıcı"]},
    {"q": "School", "a": "Okul", "options": ["Hastane", "Kütüphane", "Okul", "Park"]},
    {"q": "Bread", "a": "Ekmek", "options": ["Peynir", "Ekmek", "Et", "Süt"]},
    {"q": "Happy", "a": "Mutlu", "options": ["Üzgün", "Kızgın", "Mutlu", "Yorgun"]}
]

# --- MYMEMORY ÇEVİRİ FONKSİYONU ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()["responseData"]["translatedText"].lower()
    except: return text
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Merhaba {user_name}! 👋\nSözlük için kelime yazabilir veya test çözmek için /quiz yazabilirsin! 🧠"
    )

# --- QUİZ BAŞLATMA ---
async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Rastgele bir soru seç
    question_data = random.choice(QUIZ_QUESTIONS)
    context.user_data['current_quiz'] = question_data

    # Butonları oluştur
    keyboard = []
    for opt in question_data['options']:
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"q_ans|{opt}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🧠 **Kelimelerin Gücü Adına!**\n\nBu kelimenin anlamı nedir?\n👉 **{question_data['q']}**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}"),
         InlineKeyboardButton("🔊 Sesli Dinle", callback_data=f"ses|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("📝 Örnek Cümleler", callback_data=f"örnek|{word}")]
    ]
    await update.message.reply_text(f"🔎 **Kelime:** {word.capitalize()}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]

    # --- QUİZ CEVABI KONTROLÜ ---
    if action == "q_ans":
        current_quiz = context.user_data.get('current_quiz')
        if not current_quiz:
            await query.answer("Quiz süresi dolmuş.")
            return

        if val == current_quiz['a']:
            text = f"✅ **Tebrikler!**\n{current_quiz['q']} = {current_quiz['a']}\n\nYeni soru için /quiz yazabilirsin."
        else:
            text = f"❌ **Yanlış!**\nDoğru cevap: **{current_quiz['a']}**\n\nYılmak yok, tekrar dene! /quiz"
        
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return

    # --- DİĞER FONKSİYONLAR (Ses, Çeviri, Tanım vb.) ---
    await query.answer()
    # (Buradaki ses, çeviri, tanım mantığı önceki kodun aynısıdır, yer kaplamaması için özet geçilmiştir)
    # ... önceki get_translation ve API çağrıları burada devam eder ...
    
    # Pratik olması için çeviri ve tanım sonuçlarını burada MyMemory ve FreeDictionary üzerinden üretelim:
    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")

    result = ""
    if action == "ses":
        en_word = tr_to_en
        tts = gTTS(text=en_word, lang='en'); tts.save(f"{val}.mp3")
        with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio)
        os.remove(f"{val}.mp3"); return
    elif action == "ceviri":
        result = f"🇬🇧 **EN:** {tr_to_en.capitalize()}" if val == en_to_tr else f"🇹🇷 **TR:** {en_to_tr.capitalize()}"
    elif action == "tanim" or action == "örnek":
        search_word = tr_to_en
        res = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
        if res.status_code == 200:
            d = res.json()[0]
            result = f"📖 **Tanım:** {d['meanings'][0]['definitions'][0]['definition']}" if action == "tanim" else f"📝 **Örnek:** {d['meanings'][0]['definitions'][0].get('example', 'Örnek yok.')}"
        else: result = "Bulunamadı."

    await query.edit_message_text(text=f"🔎 **Kelime:** {val.capitalize()}\n\n{result}", reply_markup=query.message.reply_markup, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_start)) # Quiz komutunu ekledik
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
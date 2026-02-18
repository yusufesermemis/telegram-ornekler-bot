import os
import requests
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- DİNAMİK KELİME HAVUZU (Quiz İçin) ---
SEED_WORDS = [
    "achievement", "knowledge", "environment", "freedom", "journey", "opportunity",
    "challenge", "discovery", "imagination", "experience", "language", "connection",
    "adventure", "celebration", "difference", "education", "generation", "happiness",
    "intelligence", "mountain", "ocean", "passion", "quality", "reflection", "strength",
    "apple", "book", "computer", "music", "art", "science", "friend", "family"
]
DISTRACTORS = ["Masa", "Kalem", "Gelecek", "Umut", "Hızlı", "Yavaş", "Zaman", "Yolculuk", "Mavi", "Büyük", "Güzel", "Çirkin"]

# --- YARDIMCI FONKSİYONLAR ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

async def generate_quiz_list(count):
    questions = []
    # Listeden rastgele kelimeler seç
    selected_seeds = random.sample(SEED_WORDS, min(count, len(SEED_WORDS)))
    
    for word in selected_seeds:
        correct_answer = get_translation(word, "en", "tr")
        options = random.sample(DISTRACTORS, 3)
        options.append(correct_answer.capitalize())
        random.shuffle(options)
        
        questions.append({
            "q": word.capitalize(),
            "a": correct_answer.capitalize(),
            "options": options
        })
    return questions

async def send_quiz_question(query, context):
    user_data = context.user_data
    idx = user_data['quiz_idx']
    questions = user_data['quiz_list']
    
    if idx < len(questions):
        q_data = questions[idx]
        user_data['current_q'] = q_data
        # Şık butonları
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"ans|{opt}")] for opt in q_data['options']]
        text = f"📝 **Soru {idx + 1}/{len(questions)}**\n\nBu kelimenin anlamı nedir?\n👉 **{q_data['q']}**"
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        # Test Bitti
        score = user_data['quiz_score']
        await query.edit_message_text(text=f"🏁 **Test Bitti!**\n\nSkorun: **{score}/{len(questions)}**\nYeni bir test için /quiz yazabilirsin! 🚀", parse_mode="Markdown")

# --- ANA KOMUTLAR ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user}! 👋\n\n🔹 **Kelime Ara:** Herhangi bir kelime yaz.\n🔹 **Test Çöz:** /quiz yazarak kendini dene.")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("5 Soru", callback_data="set_5"),
         InlineKeyboardButton("10 Soru", callback_data="set_10")],
        [InlineKeyboardButton("15 Soru", callback_data="set_15"),
         InlineKeyboardButton("20 Soru", callback_data="set_20")]
    ]
    await update.message.reply_text("🧠 Kaç soruluk bir test çözmek istersin?", reply_markup=InlineKeyboardMarkup(keyboard))

# --- KELİME ARAMA (Düzeltilen Kısım) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    word = update.message.text.lower().strip()
    
    # Kelime butonları
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{word}")],
        [InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")]
    ]
    
    await update.message.reply_text(
        f"🔎 **Kelime:** {word.capitalize()}\nNe öğrenmek istersin?", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

# --- BUTON TIKLAMALARI ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action = data[0]
    await query.answer()

    # --- 1. QUIZ İŞLEMLERİ ---
    if action.startswith("set_"):
        count = int(action.split("_")[1])
        await query.edit_message_text("⏳ Sorular hazırlanıyor...")
        context.user_data['quiz_list'] = await generate_quiz_list(count)
        context.user_data['quiz_idx'] = 0
        context.user_data['quiz_score'] = 0
        await send_quiz_question(query, context)
        return

    if action == "ans":
        user_choice = data[1]
        current_q = context.user_data['current_q']
        if user_choice == current_q['a']:
            context.user_data['quiz_score'] += 1
            status = "✅ Doğru!"
        else:
            status = f"❌ Yanlış! (Doğru: {current_q['a']})"
        
        context.user_data['quiz_idx'] += 1
        keyboard = [[InlineKeyboardButton("Devam Et ➡️", callback_data="next_q")]]
        await query.edit_message_text(text=f"{status}\n\nSıradaki soruya geçelim mi?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == "next_q":
        await send_quiz_question(query, context)
        return

    # --- 2. KELİME ARAMA İŞLEMLERİ ---
    val = data[1] # Kelime
    
    # MyMemory Çevirileri
    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")

    result = ""

    if action == "s": # Ses (gTTS)
        en_word = tr_to_en # Ses hep İngilizce
        try:
            tts = gTTS(text=en_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: 
                await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio)
            os.remove(f"{val}.mp3")
        except: await context.bot.send_message(chat_id=query.message.chat_id, text="Ses hatası.")
        return # Mesajı düzenlemeye gerek yok

    elif action == "c": # Çeviri (MyMemory)
        if val == en_to_tr: # Zaten İngilizce ise
            result = f"🇹🇷 **Türkçe:** {en_to_tr.capitalize()}"
        else: # Türkçe ise
            result = f"🇬🇧 **İngilizce:** {tr_to_en.capitalize()}"

    elif action in ["t", "e", "o"]: # Tanım, Eş Anlam, Örnek
        search_word = tr_to_en if val != tr_to_en else val # İngilizce halini kullan
        
        # Free Dictionary API (Tanım ve Örnek)
        if action == "t" or action == "o":
            try:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        result = f"📖 **Tanım:** {defi}"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        result = f"📝 **Örnek:** _{ex}_"
                else: result = "Bilgi bulunamadı."
            except: result = "Bağlantı hatası."

        # Datamuse API (Eş Anlam)
        elif action == "e":
            try:
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [i['word'] for i in r.json()[:5]]
                result = f"🔗 **Eş Anlamlılar:** {', '.join(items)}" if items else "Bulunamadı."
            except: result = "Hata oluştu."

    # Sonucu ekrana bas
    # Eski klavyeyi korumak için butonları tekrar tanımlıyoruz
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}")],
        [InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")]
    ]
    await query.edit_message_text(
        text=f"🔎 **Kelime:** {val.capitalize()}\n\n{result}", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Komutlar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_command))
    
    # DÜZELTİLDİ: Artık metinleri handle_message fonksiyonuna yönlendiriyoruz
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
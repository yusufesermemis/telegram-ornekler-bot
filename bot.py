import os
import requests
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- DİNAMİK KELİME HAVUZU (Tohum Liste) ---
# Buraya istediğin kadar İngilizce kelime ekleyebilirsin, bot bunları canlı çevirecek.
SEED_WORDS = [
    "achievement", "knowledge", "environment", "freedom", "journey", "opportunity",
    "challenge", "discovery", "imagination", "experience", "language", "connection",
    "adventure", "celebration", "difference", "education", "generation", "happiness",
    "intelligence", "mountain", "ocean", "passion", "quality", "reflection", "strength"
]

# Yanlış şıklar için rastgele Türkçe kelime havuzu
DISTRACTORS = ["Masa", "Kalem", "Gelecek", "Umut", "Hızlı", "Yavaş", "Zaman", "Yolculuk", "Mavi", "Büyük"]

def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

async def generate_quiz_list(count):
    """Canlı API kullanarak rastgele sorular oluşturur."""
    questions = []
    selected_seeds = random.sample(SEED_WORDS, min(count, len(SEED_WORDS)))
    
    for word in selected_seeds:
        correct_answer = get_translation(word, "en", "tr")
        # Yanlış şıkları seç ve doğru cevabı araya karıştır
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
        keyboard = [[InlineKeyboardButton(opt, callback_data=f"ans|{opt}")] for opt in q_data['options']]
        text = f"📝 **Soru {idx + 1}/{len(questions)}**\n\nBu kelimenin anlamı nedir?\n👉 **{q_data['q']}**"
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        score = user_data['quiz_score']
        await query.edit_message_text(text=f"🏁 **Test Bitti!**\n\nSkorun: **{score}/{len(questions)}**\nYeni bir test için /quiz yazabilirsin! 🚀", parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! 👋 Kelime aratabilir veya /quiz ile teste başlayabilirsin.")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # İstediğin 5-10-15-20 seçeneklerini ekledik
    keyboard = [
        [InlineKeyboardButton("5 Soru", callback_data="set_5"),
         InlineKeyboardButton("10 Soru", callback_data="set_10")],
        [InlineKeyboardButton("15 Soru", callback_data="set_15"),
         InlineKeyboardButton("20 Soru", callback_data="set_20")]
    ]
    await update.message.reply_text("🧠 Kaç soruluk bir test çözmek istersin?", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action = data[0]
    await query.answer()

    if action.startswith("set_"):
        count = int(action.split("_")[1])
        await query.edit_message_text("⏳ Sorular canlı olarak hazırlanıyor, lütfen bekle...")
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

    # Sözlük fonksiyonları buraya eklenebilir (Önceki sürümlerdeki gibi)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)) # Basitleştirildi
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
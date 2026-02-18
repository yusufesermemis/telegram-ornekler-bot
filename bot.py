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

# --- KELİME & DEYİM HAVUZU ---
# Quiz için kelimeler
SEED_WORDS = ["apple", "time", "break", "leg", "money", "heart", "mind", "book", "hand", "eye", "dream", "life", "world", "friend"]
DISTRACTORS = ["Masa", "Kalem", "Gelecek", "Umut", "Hızlı", "Yavaş", "Zaman", "Yolculuk", "Mavi", "Büyük"]

# --- DEYİM VE ATASÖZÜ VERİ TABANI (Örnekler) ---
# Buraya en yaygın İngilizce deyimleri ve Türkçe karşılıklarını ekledik.
IDIOMS_POOL = [
    {"ph": "Piece of cake", "tr": "Çocuk oyuncağı (Çok kolay)", "k": ["cake", "piece", "easy"]},
    {"ph": "Break a leg", "tr": "Şeytanın bacağını kır (Bol şans)", "k": ["break", "leg", "luck"]},
    {"ph": "Kill two birds with one stone", "tr": "Bir taşla iki kuş vurmak", "k": ["bird", "stone", "kill", "two"]},
    {"ph": "Apple of my eye", "tr": "Göz bebeğim (Çok sevilen)", "k": ["apple", "eye", "love"]},
    {"ph": "Under the weather", "tr": "Keyifsiz, hasta hissetmek", "k": ["weather", "sick", "ill"]},
    {"ph": "Time flies", "tr": "Zaman su gibi akıp geçiyor", "k": ["time", "fly"]},
    {"ph": "Cost an arm and a leg", "tr": "Ateş pahası (Çok pahalı)", "k": ["arm", "leg", "cost", "money", "expensive"]},
    {"ph": "Let the cat out of the bag", "tr": "Ağzından baklayı çıkarmak (Sırrı bozmak)", "k": ["cat", "bag", "secret"]},
    {"ph": "Once in a blue moon", "tr": "Kırk yılda bir (Çok nadir)", "k": ["moon", "blue", "rare"]},
    {"ph": "No pain, no gain", "tr": "Emek olmadan yemek olmaz", "k": ["pain", "gain", "work"]},
    {"ph": "Better late than never", "tr": "Geç olsun güç olmasın", "k": ["late", "never", "better"]},
    {"ph": "Break the ice", "tr": "Buzları eritmek (Ortamı yumuşatmak)", "k": ["break", "ice"]},
    {"ph": "Hit the sack", "tr": "Kafayı vurup yatmak", "k": ["hit", "sack", "sleep", "bed"]},
    {"ph": "Miss the boat", "tr": "Fırsatı kaçırmak", "k": ["miss", "boat", "chance"]},
    {"ph": "Speak of the devil", "tr": "İti an çomağı hazırla", "k": ["speak", "devil"]},
    {"ph": "See eye to eye", "tr": "Aynı fikirde olmak", "k": ["see", "eye", "agree"]},
    {"ph": "When pigs fly", "tr": "Çıkmaz ayın son çarşambası (Asla)", "k": ["pig", "fly", "never"]},
    {"ph": "Actions speak louder than words", "tr": "Lafla peynir gemisi yürümez", "k": ["action", "word", "speak"]},
    {"ph": "Don't judge a book by its cover", "tr": "Kimseyi dış görünüşüne göre yargılama", "k": ["book", "cover", "judge"]},
    {"ph": "Call it a day", "tr": "Paydos etmek, günü bitirmek", "k": ["call", "day", "work"]}
]

def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

# --- DEYİM ARAMA FONKSİYONU ---
def find_idioms(word):
    found = []
    word = word.lower()
    for item in IDIOMS_POOL:
        # Aranan kelime deyimin içinde geçiyor mu veya anahtar kelimelerden biri mi?
        if word in item['ph'].lower() or word in item['k']:
            found.append(f"🎭 **{item['ph']}**\n💡 _{item['tr']}_")
    return found[:3] # En fazla 3 tane göster

# --- QUIZ FONKSİYONLARI ---
async def generate_quiz_list(count):
    questions = []
    selected_seeds = random.sample(SEED_WORDS, min(count, len(SEED_WORDS)))
    for word in selected_seeds:
        correct_answer = get_translation(word, "en", "tr")
        options = random.sample(DISTRACTORS, 3)
        options.append(correct_answer.capitalize())
        random.shuffle(options)
        questions.append({"q": word.capitalize(), "a": correct_answer.capitalize(), "options": options})
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
        await query.edit_message_text(text=f"🏁 **Test Bitti!**\n\nSkorun: **{score}/{len(questions)}**\nYeni test için: /quiz", parse_mode="Markdown")

# --- ANA KOMUTLAR ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! 👋\n🔹 Kelime yazarak çeviri ve deyimlere bakabilir,\n🔹 /quiz yazarak kendini test edebilirsin!")

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("5 Soru", callback_data="set_5"), InlineKeyboardButton("10 Soru", callback_data="set_10")]]
    await update.message.reply_text("🧠 Kaç soru çözmek istersin?", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text: return
    word = update.message.text.lower().strip()
    
    # Klavye Düzeni: Deyimler butonunu ekledik
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{word}"),
         InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{word}")] # Yeni Buton!
    ]
    await update.message.reply_text(f"🔎 **Kelime:** {word.capitalize()}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action = data[0]
    await query.answer()

    # Quiz Mantığı
    if action.startswith("set_"):
        count = int(action.split("_")[1])
        await query.edit_message_text("⏳ Hazırlanıyor...")
        context.user_data['quiz_list'] = await generate_quiz_list(count)
        context.user_data['quiz_idx'] = 0; context.user_data['quiz_score'] = 0
        await send_quiz_question(query, context); return
    if action == "ans":
        status = "✅ Doğru!" if data[1] == context.user_data['current_q']['a'] else f"❌ Yanlış! (Cevap: {context.user_data['current_q']['a']})"
        context.user_data['quiz_score'] += (1 if "Doğru" in status else 0); context.user_data['quiz_idx'] += 1
        await query.edit_message_text(f"{status}\n\nDevam?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️", callback_data="next_q")]]))
        return
    if action == "next_q": await send_quiz_question(query, context); return

    # Kelime İşlemleri
    val = data[1]
    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")
    result = ""

    if action == "s": # Ses
        try:
            tts = gTTS(text=tr_to_en, lang='en'); tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as f: await context.bot.send_voice(query.message.chat_id, f)
            os.remove(f"{val}.mp3")
        except: pass; return

    elif action == "c": result = f"🇹🇷 **TR:** {en_to_tr.capitalize()}" if val == en_to_tr else f"🇬🇧 **EN:** {tr_to_en.capitalize()}"
    
    elif action == "i": # DEYİMLER (Yeni Özellik)
        idioms = find_idioms(tr_to_en if val != tr_to_en else val)
        if idioms: result = "\n\n".join(idioms)
        else: result = "⚠️ Bu kelimeyle ilgili kayıtlı bir deyim bulamadım."

    elif action in ["t", "o", "e"]: # Tanım, Örnek, Eş Anlam
        search_word = tr_to_en if val != tr_to_en else val
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [i['word'] for i in r.json()[:5]]
                result = f"🔗 **Eş Anlamlılar:** {', '.join(items)}" if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    result = f"📖 **Tanım:** {d['meanings'][0]['definitions'][0]['definition']}" if action == "t" else f"📝 **Örnek:** _{d['meanings'][0]['definitions'][0].get('example', 'Örnek yok.')}_"
                else: result = "Bilgi bulunamadı."
        except: result = "Hata."

    # Butonları tekrar göster
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"), InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"), InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}"), InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{val}")]
    ]
    await query.edit_message_text(text=f"🔎 **Kelime:** {val.capitalize()}\n\n{result}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
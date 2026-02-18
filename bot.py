import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- DEYİM VERİ TABANI ---
IDIOMS_POOL = [
    {"ph": "Piece of cake", "tr": "Çocuk oyuncağı (Çok kolay)", "k": ["cake", "piece", "easy"]},
    {"ph": "Break a leg", "tr": "Şeytanın bacağını kır (Bol şans)", "k": ["break", "leg", "luck"]},
    {"ph": "Kill two birds with one stone", "tr": "Bir taşla iki kuş vurmak", "k": ["bird", "stone", "kill", "two"]},
    {"ph": "Apple of my eye", "tr": "Göz bebeğim", "k": ["apple", "eye", "love"]},
    {"ph": "Under the weather", "tr": "Keyifsiz, hasta hissetmek", "k": ["weather", "sick", "ill"]},
    {"ph": "Time flies", "tr": "Zaman su gibi akıp geçiyor", "k": ["time", "fly"]},
    {"ph": "Cost an arm and a leg", "tr": "Ateş pahası (Çok pahalı)", "k": ["arm", "leg", "cost", "money", "expensive"]},
    {"ph": "Let the cat out of the bag", "tr": "Ağzından baklayı çıkarmak", "k": ["cat", "bag", "secret"]},
    {"ph": "Once in a blue moon", "tr": "Kırk yılda bir", "k": ["moon", "blue", "rare"]},
    {"ph": "No pain, no gain", "tr": "Emek olmadan yemek olmaz", "k": ["pain", "gain", "work"]},
    {"ph": "Better late than never", "tr": "Geç olsun güç olmasın", "k": ["late", "never", "better"]},
    {"ph": "Break the ice", "tr": "Buzları eritmek", "k": ["break", "ice"]},
    {"ph": "Hit the sack", "tr": "Kafayı vurup yatmak", "k": ["hit", "sack", "sleep", "bed"]},
    {"ph": "Miss the boat", "tr": "Fırsatı kaçırmak", "k": ["miss", "boat", "chance"]},
    {"ph": "Speak of the devil", "tr": "İti an çomağı hazırla", "k": ["speak", "devil"]},
    {"ph": "See eye to eye", "tr": "Aynı fikirde olmak", "k": ["see", "eye", "agree"]},
    {"ph": "When pigs fly", "tr": "Çıkmaz ayın son çarşambası", "k": ["pig", "fly", "never"]},
    {"ph": "Actions speak louder than words", "tr": "Lafla peynir gemisi yürümez", "k": ["action", "word", "speak"]},
    {"ph": "Don't judge a book by its cover", "tr": "Görünüşe aldanma", "k": ["book", "cover", "judge"]},
    {"ph": "Call it a day", "tr": "Paydos etmek", "k": ["call", "day", "work"]}
]

def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        return res.json()["responseData"]["translatedText"].lower() if res.status_code == 200 else text
    except: return text

def find_idioms(word):
    found = []
    word = word.lower()
    for item in IDIOMS_POOL:
        if word in item['ph'].lower() or word in item['k']:
            # Tasarım: Deyimleri madde işaretiyle listele
            found.append(f"🔹 *{item['ph']}*\n    _Anlamı: {item['tr']}_")
    return found[:3]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    # Tasarım: Başlangıç mesajını süsledik
    msg = (
        f"👋 **Merhaba {user}!**\n\n"
        "Ben senin kişisel İngilizce koçunum. 🚀\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Bana herhangi bir kelime yaz, sana şunları sunayım:\n\n"
        "🇹🇷 **Tam Çeviri**\n"
        "📖 **Sözlük Tanımı**\n"
        "🎭 **İlgili Deyimler**\n"
        "🔊 **Sesli Telaffuz**\n\n"
        "_Hadi, ilk kelimeni yaz!_ 👇"
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
         InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{word}")]
    ]
    
    # Tasarım: Aranan kelimeyi büyük başlık yapıyoruz
    header = f"🔎 **KELİME:** `{word.upper()}`\n━━━━━━━━━━━━━━━━━━\n_Ne öğrenmek istersin?_"
    
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    await query.answer()

    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")
    
    # Tasarım şablonu
    header = f"🔎 **KELİME:** `{val.upper()}`\n"
    content = ""

    # 1. ÇEVİRİ
    if action == "c":
        if en_to_tr != val: # Kelime İngilizce
            content = (
                "🇹🇷 **TÜRKÇE ANLAMI**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"✨ `{en_to_tr.upper()}`"
            )
        else: # Kelime Türkçe
            content = (
                "🇬🇧 **İNGİLİZCE KARŞILIĞI**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"✨ `{tr_to_en.upper()}`"
            )

    # 2. SES (Tasarım gerekmez, ses dosyası)
    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # 3. DEYİMLER (Tasarım: Listeleme)
    elif action == "i":
        search_word = val if en_to_tr != val else tr_to_en
        idioms = find_idioms(search_word)
        if idioms:
            content = "🎭 **İLGİLİ DEYİMLER**\n━━━━━━━━━━━━━━━━━━\n" + "\n\n".join(idioms)
        else:
            content = "⚠️ _Bu kelimeyle ilgili veri tabanımda kayıtlı bir deyim bulunamadı._"

    # 4. TANIM / ÖRNEK / EŞ ANLAM
    elif action in ["t", "o", "e"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [f"`{i['word']}`" for i in r.json()[:5]] # Kelimeleri vurgula
                content = "🔗 **EŞ ANLAMLI KELİMELER**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        content = f"📖 **İNGİLİZCE TANIM**\n━━━━━━━━━━━━━━━━━━\n_{defi}_"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        content = f"📝 **ÖRNEK CÜMLE**\n━━━━━━━━━━━━━━━━━━\n_“{ex}”_"
                else: content = "🚫 _Bilgi bulunamadı._"
        except: content = "🚫 _Bağlantı hatası._"

    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}"),
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
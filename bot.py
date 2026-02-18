import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from gtts import gTTS

# Loglama ayarları
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- DEYİM VE ATASÖZÜ VERİ TABANI ---
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

# --- MyMemory Çeviri Fonksiyonu ---
def get_translation(text, source, target):
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source}|{target}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.json()["responseData"]["translatedText"].lower()
    except:
        return text
    return text

# --- Deyim Bulma Fonksiyonu ---
def find_idioms(word):
    found = []
    word = word.lower()
    for item in IDIOMS_POOL:
        if word in item['ph'].lower() or word in item['k']:
            found.append(f"🎭 **{item['ph']}**\n💡 _{item['tr']}_")
    return found[:3]

# --- Başlangıç Komutu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user}! 👋\nİstediğin kelimeyi yaz, hemen çevireyim, tanımlayayım ve deyimlerini bulayım! 🚀")

# --- Mesaj Yakalama ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    word = update.message.text.lower().strip()
    
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{word}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{word}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{word}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{word}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{word}"),
         InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{word}")]
    ]
    
    await update.message.reply_text(
        f"🔎 **Kelime:** {word.capitalize()}", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

# --- Buton İşlemleri ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action = data[0]
    val = data[1] # İşlem yapılan kelime

    await query.answer()

    # Çevirileri al
    tr_to_en = get_translation(val, "tr", "en") # Türkçe girildiyse İngilizcesi
    en_to_tr = get_translation(val, "en", "tr") # İngilizce girildiyse Türkçesi

    result_content = ""

    # --- 1. ÇEVİRİ MANTIĞI (DÜZELTİLDİ) ---
    if action == "c":
        # Mantık: Eğer 'en_to_tr' sonucu, kelimenin kendisinden farklıysa
        # (Örn: great -> harika), demek ki kelime İngilizceydi ve başarıyla çevrildi.
        if en_to_tr != val:
            result_content = f"🇹🇷 **Türkçe:** {en_to_tr.capitalize()}"
        else:
            # Değilse, kelime Türkçedir, İngilizce karşılığını göster.
            result_content = f"🇬🇧 **İngilizce:** {tr_to_en.capitalize()}"

    # --- 2. SES (gTTS) ---
    elif action == "s":
        # Ses için her zaman İngilizce versiyonu kullan
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio:
                await context.bot.send_voice(chat_id=query.message.chat_id, voice=audio)
            os.remove(f"{val}.mp3")
            return # Ses gönderince mesajı editlemeye gerek yok
        except:
            await context.bot.send_message(chat_id=query.message.chat_id, text="Ses hatası.")
            return

    # --- 3. DEYİMLER ---
    elif action == "i":
        # Deyim ararken kelimenin İngilizcesini kullan
        search_word = val if en_to_tr != val else tr_to_en
        idioms = find_idioms(search_word)
        if idioms:
            result_content = "\n\n".join(idioms)
        else:
            result_content = "⚠️ Bu kelimeyle ilgili veri tabanımda deyim yok."

    # --- 4. TANIM / ÖRNEK / EŞ ANLAM ---
    elif action in ["t", "o", "e"]:
        # API aramaları için İngilizce kelimeyi belirle
        search_word = val if en_to_tr != val else tr_to_en
        
        try:
            if action == "e": # Eş Anlam (Datamuse)
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [i['word'] for i in r.json()[:5]]
                result_content = f"🔗 **Eş Anlamlılar:** {', '.join(items)}" if items else "Bulunamadı."
            else: # Tanım ve Örnek (Free Dictionary API)
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        result_content = f"📖 **Tanım:** {defi}"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        result_content = f"📝 **Örnek:** _{ex}_"
                else: result_content = "Bilgi bulunamadı."
        except: result_content = "Bağlantı hatası."

    # Sonucu göster (Klavye sabit kalsın)
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"c|{val}"),
         InlineKeyboardButton("🔊 Dinle", callback_data=f"s|{val}")],
        [InlineKeyboardButton("📖 Tanım", callback_data=f"t|{val}"),
         InlineKeyboardButton("📝 Örnek", callback_data=f"o|{val}")],
        [InlineKeyboardButton("🔗 Eş Anlam", callback_data=f"e|{val}"),
         InlineKeyboardButton("🎭 Deyimler", callback_data=f"i|{val}")]
    ]
    
    await query.edit_message_text(
        text=f"🔎 **Kelime:** {val.capitalize()}\n\n{result_content}", 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode="Markdown"
    )

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
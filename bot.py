import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Loglama ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Bir İngilizce kelime yaz; sana anlamını, çevirisini ve Güçlü eş anlamlılarını getireyim. 🇹🇷🇬🇧")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # "Yazıyor..." aksiyonu
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # --- 1. ADIM: İNGİLİZCE TANIM (DictionaryAPI) ---
    url_def = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    english_def = "Tanım bulunamadı."
    
    try:
        response_def = requests.get(url_def, timeout=5)
        if response_def.status_code == 200:
            data_def = response_def.json()
            # İlk anlamı çekiyoruz
            if isinstance(data_def, list) and len(data_def) > 0:
                meanings = data_def[0].get("meanings", [])
                if meanings:
                    definitions = meanings[0].get("definitions", [])
                    if definitions:
                        english_def = definitions[0].get("definition", "Tanım yok.")
    except Exception as e:
        print(f"Tanım Hatası: {e}")

    # --- 2. ADIM: EŞ ANLAMLILAR (Datamuse API - Yeni Eklenen Kısım) ---
    # Datamuse, 'rel_syn' (related synonyms) parametresiyle çalışır.
    url_syn = f"https://api.datamuse.com/words?rel_syn={word}"
    synonyms_text = "Bulunamadı"

    try:
        response_syn = requests.get(url_syn, timeout=5)
        if response_syn.status_code == 200:
            data_syn = response_syn.json()
            # Gelen veri şöyledir: [{"word": "happy", "score": 100}, ...]
            # En yüksek puanlı ilk 7 kelimeyi alalım
            syn_list = [item['word'] for item in data_syn[:7]]
            
            if syn_list:
                synonyms_text = ", ".join(syn_list)
    except Exception as e:
        print(f"Eş Anlamlı Hatası: {e}")

    # --- 3. ADIM: TÜRKÇE ÇEVİRİ (Deep Translator) ---
    try:
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(word)
    except Exception:
        turkish_meaning = "Çeviri yapılamadı."

    # --- 4. ADIM: MESAJI BİRLEŞTİR VE GÖNDER ---
    reply_text = (
        f"🔤 **Kelime:** {word.capitalize()}\n\n"
        f"🇹🇷 **Türkçesi:** {turkish_meaning.capitalize()}\n"
        f"🇬🇧 **Tanımı:** {english_def}\n"
        f"🔥 **Güçlü Eş Anlamlılar:** _{synonyms_text}_"
    )

    await update.message.reply_text(reply_text, parse_mode="Markdown")

def main():
    if not TOKEN:
        print("HATA: TOKEN bulunamadı!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
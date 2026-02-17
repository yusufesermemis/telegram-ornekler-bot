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
    await update.message.reply_text("Merhaba! Kelimeyi yaz, gerisini bana bırak. 🇹🇷↔🇬🇧")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user_input = update.message.text.lower().strip()
    
    # "Yazıyor..." aksiyonu
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # --- 1. ADIM: AKILLI ÇEVİRİ ---
    try:
        # İngilizce karşılığını bul (API araması için lazım)
        target_word = GoogleTranslator(source='auto', target='en').translate(user_input).lower()
        
        # Türkçe karşılığını bul (Kullanıcıya göstermek için)
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(user_input).lower()
    except Exception:
        target_word = user_input
        turkish_meaning = user_input

    # --- 2. ADIM: İNGİLİZCE TANIM ÇEKME ---
    url_def = f"https://api.dictionaryapi.dev/api/v2/entries/en/{target_word}"
    english_def = "Tanım bulunamadı."
    
    try:
        response_def = requests.get(url_def, timeout=5)
        if response_def.status_code == 200:
            data_def = response_def.json()
            if isinstance(data_def, list) and len(data_def) > 0:
                meanings = data_def[0].get("meanings", [])
                if meanings:
                    definitions = meanings[0].get("definitions", [])
                    if definitions:
                        english_def = definitions[0].get("definition", "Tanım yok.")
    except Exception as e:
        print(f"Tanım Hatası: {e}")

    # --- 3. ADIM: EŞ ANLAMLILAR ---
    url_syn = f"https://api.datamuse.com/words?rel_syn={target_word}"
    synonyms_text = "Bulunamadı"

    try:
        response_syn = requests.get(url_syn, timeout=5)
        if response_syn.status_code == 200:
            data_syn = response_syn.json()
            syn_list = [item['word'] for item in data_syn[:7]]
            if syn_list:
                synonyms_text = ", ".join(syn_list)
    except Exception:
        pass

    # --- 4. ADIM: MESAJI OLUŞTURMA ---
    
    # Başlık: Aranan kelimeyi gösterelim
    header = f"🔎 **Aranan:** {user_input.capitalize()}"
    
    # Eğer çeviri yapıldıysa (Türkçe -> İngilizce gibi), okun ucunu da gösterelim
    if user_input != target_word:
        header += f" ➡️ **{target_word.capitalize()}**"

    parts = [header, ""] # Görsel boşluk için
    
    # KONTROL: Eğer kullanıcının yazdığı ile çeviri aynıysa, "Türkçe Anlamı" satırını ekleme!
    if user_input != turkish_meaning:
        parts.append(f"🇹🇷 **Türkçe Anlamı:** {turkish_meaning.capitalize()}")
    
    # İŞTE BURASI DEĞİŞTİ: Artık bayrak var 🇬🇧
    parts.append(f"🇬🇧 **İngilizce Tanımı:** {english_def}")
    parts.append(f"🔥 **Eş Anlamlılar:** _{synonyms_text}_")

    reply_text = "\n".join(parts)

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
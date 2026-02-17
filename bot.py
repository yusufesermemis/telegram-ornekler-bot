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
    await update.message.reply_text("Merhaba! Bir İngilizce kelime yaz; sana anlamını, çevirisini ve eş anlamlılarını getireyim. 🇹🇷🇬🇧")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # "Yazıyor..." aksiyonu
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 1. API İSTEĞİ (İngilizce Tanım ve Eş Anlamlılar)
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    english_def = "Tanım bulunamadı."
    synonyms_list = [] # Eş anlamlıları burada toplayacağız

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Tanımı al
            if isinstance(data, list) and len(data) > 0:
                meanings = data[0].get("meanings", [])
                if meanings:
                    definitions = meanings[0].get("definitions", [])
                    if definitions:
                        english_def = definitions[0].get("definition", "Tanım yok.")
            
            # Eş anlamlıları topla (API'de farklı yerlerde olabiliyor, hepsini tarıyoruz)
            for item in data:
                for meaning in item.get("meanings", []):
                    # Ana kısımdaki eş anlamlılar
                    if "synonyms" in meaning:
                        for syn in meaning["synonyms"]:
                            synonyms_list.append(syn)
                    
                    # Alt tanımlardaki eş anlamlılar
                    for definition in meaning.get("definitions", []):
                        if "synonyms" in definition:
                            for syn in definition["synonyms"]:
                                synonyms_list.append(syn)

    except Exception as e:
        english_def = "Bağlantı hatası."
        print(f"Hata: {e}")

    # 2. TÜRKÇE ÇEVİRİ
    try:
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(word)
    except Exception:
        turkish_meaning = "Çeviri yapılamadı."

    # 3. EŞ ANLAMLILARI DÜZENLEME
    # Listeyi temizle (aynı kelime tekrar etmesin) ve ilk 5 tanesini al
    unique_synonyms = list(set(synonyms_list)) 
    
    if unique_synonyms:
        # Sadece ilk 5 tanesini al
        synonyms_text = ", ".join(unique_synonyms[:5]) 
    else:
        synonyms_text = "Bulunamadı"

    # 4. MESAJI OLUŞTUR VE GÖNDER
    reply_text = (
        f"🔤 **Kelime:** {word.capitalize()}\n\n"
        f"🇹🇷 **Türkçesi:** {turkish_meaning.capitalize()}\n"
        f"📖 **Tanım:** {english_def}\n"
        f"🔄 **Eş Anlamlılar:** _{synonyms_text}_"
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
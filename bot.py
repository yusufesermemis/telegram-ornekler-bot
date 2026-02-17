import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Loglama ayarları (Hata takibi için)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kullanıcının ismini alalım
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user_name}! 👋\nBana Türkçe veya İngilizce bir kelime yaz, senin için çevirip detaylarını getireyim. 🇹🇷↔🇬🇧")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # Kullanıcının yazdığı kelime ve ismi
    user_input = update.message.text.lower().strip()
    user_name = update.effective_user.first_name
    
    # "Yazıyor..." aksiyonu (Botun düşündüğünü gösterir)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # --- 1. ADIM: AKILLI ÇEVİRİ VE DİL TESPİTİ ---
    try:
        # İngilizce karşılığını bul (API araması ve başlık için lazım)
        target_word = GoogleTranslator(source='auto', target='en').translate(user_input).lower()
        
        # Türkçe karşılığını bul (Kullanıcıya göstermek için)
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(user_input).lower()
    except Exception:
        # Çeviri servisi hata verirse olduğu gibi bırak
        target_word = user_input
        turkish_meaning = user_input

    # --- 2. ADIM: İNGİLİZCE TANIM ÇEKME (Dictionary API) ---
    # Aramayı her zaman İngilizce kelime (target_word) üzerinden yapıyoruz
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

    # --- 3. ADIM: GÜÇLÜ EŞ ANLAMLILAR (Datamuse API) ---
    url_syn = f"https://api.datamuse.com/words?rel_syn={target_word}"
    synonyms_text = "Bulunamadı"

    try:
        response_syn = requests.get(url_syn, timeout=5)
        if response_syn.status_code == 200:
            data_syn = response_syn.json()
            # En alakalı ilk 7 kelimeyi al
            syn_list = [item['word'] for item in data_syn[:7]]
            if syn_list:
                synonyms_text = ", ".join(syn_list)
    except Exception:
        pass

    # --- 4. ADIM: MESAJI OLUŞTURMA ---
    
    # Başlık: Kullanıcının yazdığı kelime
    header = f"🔎 **Kelime:** {user_input.capitalize()}"
    
    # Eğer kelime çevrildiyse (Yani Türkçe yazıldıysa), yanına İngilizcesini ekle
    if user_input != target_word:
        header += f" ➡️ 🇬🇧 **{target_word.capitalize()}**"

    parts = [header, ""] # Görsel boşluk
    
    # KONTROL: Eğer kullanıcının yazdığı zaten Türkçe ise "Türkçe Anlamı" satırını gizle
    if user_input != turkish_meaning:
        parts.append(f"🇹🇷 **Türkçe Anlamı:** {turkish_meaning.capitalize()}")
    
    # İngilizce Tanım ve Eş Anlamlılar (Her zaman gösterilir)
    parts.append(f"🇬🇧 **İngilizce Tanımı:** {english_def}")
    parts.append(f"🔥 **Eş Anlamlılar:** _{synonyms_text}_")
    
    # Altına küçük bir imza ekleyelim (Opsiyonel)
    parts.append(f"\n_Umarım yardımcı olmuştur, {user_name}!_")

    reply_text = "\n".join(parts)

    await update.message.reply_text(reply_text, parse_mode="Markdown")

def main():
    if not TOKEN:
        print("HATA: TOKEN bulunamadı! Lütfen .env dosyasını veya Railway Variables kısmını kontrol et.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
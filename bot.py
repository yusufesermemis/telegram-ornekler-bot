import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Loglama
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv("TOKEN")

# --- KOMUTLAR ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(f"Merhaba {user_name}! 👋\nBir kelime yaz, sana seçenekler sunayım.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # Butonları hazırlıyoruz
    # callback_data: Butona basılınca arka planda bota gönderilen gizli veri
    keyboard = [
        [InlineKeyboardButton("🇹🇷 Türkçe Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")],
        [InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔎 **Kelime:** {word.capitalize()}\nNe öğrenmek istersin?", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- BUTON TIKLAMALARINI YAKALAYAN FONKSİYON ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Tıklamayı al
    query = update.callback_query
    await query.answer() # "Yükleniyor" ikonunu durdur
    
    # Gelen veriyi ayrıştır (Örn: "ceviri|apple")
    data = query.data.split("|")
    action = data[0] # ceviri, tanim veya esanlam
    word = data[1]   # kelimenin kendisi

    result_text = ""

    # 1. ÇEVİRİ BUTONU TIKLANDIYSA
    if action == "ceviri":
        try:
            translated = GoogleTranslator(source='auto', target='tr').translate(word)
            result_text = f"🔎 **{word.capitalize()}**\n🇹🇷 **Türkçesi:** {translated.capitalize()}"
        except:
            result_text = "Çeviri servisine ulaşılamadı."

    # 2. TANIM BUTONU TIKLANDIYSA
    elif action == "tanim":
        try:
            # İngilizce değilse önce İngilizceye çevir
            target_word = GoogleTranslator(source='auto', target='en').translate(word).lower()
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{target_word}"
            
            response = requests.get(url, timeout=5)
            definition = "Tanım bulunamadı."
            
            if response.status_code == 200:
                data = response.json()
                definition = data[0]["meanings"][0]["definitions"][0]["definition"]
            
            result_text = f"🔎 **{word.capitalize()}**\n📖 **Tanım:** {definition}"
        except:
            result_text = "Tanım servisine ulaşılamadı."

    # 3. EŞ ANLAM BUTONU TIKLANDIYSA
    elif action == "esanlam":
        try:
            target_word = GoogleTranslator(source='auto', target='en').translate(word).lower()
            url = f"https://api.datamuse.com/words?rel_syn={target_word}"
            
            response = requests.get(url, timeout=5)
            synonyms = "Bulunamadı"
            
            if response.status_code == 200:
                data = response.json()
                items = [item['word'] for item in data[:5]]
                if items:
                    synonyms = ", ".join(items)
            
            result_text = f"🔎 **{word.capitalize()}**\n🔥 **Eş Anlamlılar:** _{synonyms}_"
        except:
            result_text = "Veri alınamadı."

    # Mevcut mesajı güncelle (Butonları koruyarak)
    # Butonları tekrar koyuyoruz ki kullanıcı başka bir şeye de bakabilsin
    keyboard = [
        [InlineKeyboardButton("🇹🇷 Türkçe Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")],
        [InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mesajı düzenle
    await query.edit_message_text(text=result_text, reply_markup=reply_markup, parse_mode="Markdown")

def main():
    if not TOKEN:
        print("HATA: TOKEN yok.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Buton tıklamalarını dinleyen yeni bir handler ekledik
    app.add_handler(CallbackQueryHandler(button_click))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
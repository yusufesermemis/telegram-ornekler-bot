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
    
    # Arka planda kelimenin dilini anlamak için hızlıca bir çeviri kontrolü yapıyoruz
    show_translate_button = True
    try:
        translated_check = GoogleTranslator(source='auto', target='tr').translate(word).lower()
        # Eğer kelime zaten Türkçe ise (örneğin "elma" == "elma"), çeviri butonuna gerek yok
        if word == translated_check:
            show_translate_button = False
    except:
        pass # Hata olursa varsayılan olarak butonu göster

    # --- BUTONLARI HAZIRLAMA KISMI ---
    keyboard = []

    # 1. Eğer kelime Türkçe değilse "Türkçe Çeviri" butonunu ekle
    if show_translate_button:
        keyboard.append([InlineKeyboardButton("🇹🇷 Türkçe Çeviri", callback_data=f"ceviri|{word}")])
    
    # 2. Diğer butonlar her zaman görünsün
    keyboard.append([InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")])
    keyboard.append([InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔎 **Kelime:** {word.capitalize()}\nNe öğrenmek istersin?", 
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# --- BUTON TIKLAMALARINI YAKALAYAN FONKSİYON ---
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    data = query.data.split("|")
    action = data[0]
    word = data[1]

    result_text = ""
    
    # Butonları tekrar hesaplamamız lazım (ki güncel mesajda da doğru butonlar kalsın)
    show_translate_button = True
    try:
        translated_check = GoogleTranslator(source='auto', target='tr').translate(word).lower()
        if word == translated_check:
            show_translate_button = False
    except:
        pass

    keyboard = []
    if show_translate_button:
        keyboard.append([InlineKeyboardButton("🇹🇷 Türkçe Çeviri", callback_data=f"ceviri|{word}")])
    keyboard.append([InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}")])
    keyboard.append([InlineKeyboardButton("🔄 Eş Anlamlılar", callback_data=f"esanlam|{word}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    # --- İŞLEMLER ---
    if action == "ceviri":
        try:
            translated = GoogleTranslator(source='auto', target='tr').translate(word)
            result_text = f"🔎 **{word.capitalize()}**\n🇹🇷 **Türkçesi:** {translated.capitalize()}"
        except:
            result_text = "Çeviri servisine ulaşılamadı."

    elif action == "tanim":
        try:
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

    # Mesajı güncelle
    await query.edit_message_text(text=result_text, reply_markup=reply_markup, parse_mode="Markdown")

def main():
    if not TOKEN:
        print("HATA: TOKEN yok.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))

    print("Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
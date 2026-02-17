import os
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

# Loglama
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Merhaba {user_name}! 👋\nKelimeyi yaz, neyi görmek istediğini seç.\n"
        f"⭐ Favorilerini görmek için /listem yazabilirsin."
    )

# --- YENİ KOMUT: FAVORİ LİSTESİNİ GÖSTER ---
async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favs = context.user_data.get('favorites', [])
    if not favs:
        await update.message.reply_text("Henüz favori kelimen yok. ⭐ butonuyla ekleyebilirsin!")
    else:
        mesaj = "⭐ **Favori Kelimelerin:**\n\n" + "\n".join([f"• {w.capitalize()}" for w in favs])
        await update.message.reply_text(mesaj, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    header_text = f"🔎 **Kelime:** {word.capitalize()}"

    # Butonlar: Favori butonu eklendi
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("⭐ Favorilere Ekle", callback_data=f"fav|{word}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"{header_text}\nLütfen bir işlem seçin:", reply_markup=reply_markup, parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, word = data[0], data[1]

    result_content = ""
    
    # 1. FAVORİYE EKLEME İŞLEMİ
    if action == "fav":
        if 'favorites' not in context.user_data:
            context.user_data['favorites'] = []
        
        if word not in context.user_data['favorites']:
            context.user_data['favorites'].append(word)
            await query.answer(f"'{word}' listene eklendi! ⭐")
        else:
            await query.answer(f"'{word}' zaten listende. ✅")
        return # Mesajı güncellemeye gerek yok, sadece bildirim veriyoruz

    await query.answer()

    # Çeviri hazırlıkları
    try:
        en_res = GoogleTranslator(source='auto', target='en').translate(word).lower()
        tr_res = GoogleTranslator(source='auto', target='tr').translate(word).lower()
    except:
        en_res, tr_res = word, word

    if action == "ceviri":
        result_content = f"🇬🇧 **İngilizce:** {en_res.capitalize()}" if word == tr_res else f"🇹🇷 **Türkçe:** {tr_res.capitalize()}"
    elif action == "tanim":
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{en_res}"
            res = requests.get(url, timeout=5)
            result_content = f"📖 **Tanım:** {res.json()[0]['meanings'][0]['definitions'][0]['definition']}" if res.status_code == 200 else "Tanım bulunamadı."
        except: result_content = "Hata oluştu."
    elif action == "esanlam":
        try:
            url = f"https://api.datamuse.com/words?rel_syn={en_res}"
            res = requests.get(url, timeout=5)
            items = [item['word'] for item in res.json()[:5]]
            result_content = f"🔗 **Eş Anlamlılar:** _{', '.join(items)}_" if items else "Bulunamadı."
        except: result_content = "Hata oluştu."

    # Klavye (Favori butonu dahil)
    keyboard = [
        [InlineKeyboardButton("🇹🇷/🇬🇧 Çeviri", callback_data=f"ceviri|{word}")],
        [InlineKeyboardButton("📖 İngilizce Tanım", callback_data=f"tanim|{word}"),
         InlineKeyboardButton("🔗 Eş Anlamlılar", callback_data=f"esanlam|{word}")],
        [InlineKeyboardButton("⭐ Favorilere Ekle", callback_data=f"fav|{word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"🔎 **Kelime:** {word.capitalize()}\n\n{result_content}", reply_markup=reply_markup, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("listem", show_favorites)) # Yeni komut
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    app.run_polling()

if __name__ == "__main__":
    main()
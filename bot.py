async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    word = update.message.text.lower().strip()
    
    # "Yazıyor..." aksiyonu
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # 1. API İSTEĞİ
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    english_def = "Tanım bulunamadı."
    synonyms_list = [] # Eş anlamlıları burada toplayacağız

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Tanımı al
            english_def = data[0]["meanings"][0]["definitions"][0]["definition"]
            
            # Eş anlamlıları topla (API'de farklı yerlerde olabiliyor, hepsini tarıyoruz)
            for meaning in data[0]["meanings"]:
                # Ana kısımdaki eş anlamlılar
                if "synonyms" in meaning:
                    for syn in meaning["synonyms"]:
                        synonyms_list.append(syn)
                
                # Alt tanımlardaki eş anlamlılar
                for definition in meaning.get("definitions", []):
                    if "synonyms" in definition:
                        for syn in definition["synonyms"]:
                            synonyms_list.append(syn)

    except Exception:
        english_def = "Bağlantı hatası."

    # 2. TÜRKÇE ÇEVİRİ
    try:
        turkish_meaning = GoogleTranslator(source='auto', target='tr').translate(word)
    except Exception:
        turkish_meaning = "Çeviri yapılamadı."

    # 3. EŞ ANLAMLILARI DÜZENLEME
    # Listeyi temizle (aynı kelime tekrar etmesin) ve ilk 5 tanesini al
    unique_synonyms = list(set(synonyms_list)) 
    
    if unique_synonyms:
        synonyms_text = ", ".join(unique_synonyms[:5]) # İlk 5 tanesini virgülle birleştir
    else:
        synonyms_text = "Bulunamadı (None)"

    # 4. MESAJI OLUŞTUR VE GÖNDER
    reply_text = (
        f"🔤 **Kelime:** {word.capitalize()}\n\n"
        f"🇹🇷 **Türkçesi:** {turkish_meaning.capitalize()}\n"
        f"📖 **Tanım:** {english_def}\n"
        f"🔄 **Eş Anlamlılar:** _{synonyms_text}_"
    )

    await update.message.reply_text(reply_text, parse_mode="Markdown")
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

# --- TEK PARÇA DEYİM VE ATASÖZÜ HAVUZU ---
IDIOMS_POOL = [
    {"ph": "Break the ice", "tr": "Buzları eritmek, ortamı yumuşatmak", "k": ["break", "ice", "relax", "meet"]},
    {"ph": "Let the cat out of the bag", "tr": "Ağzından kaçırmak, sırrı bozmak", "k": ["cat", "bag", "secret", "tell"]},
    {"ph": "Be in two minds", "tr": "İki arada bir derede kalmak, kararsız olmak", "k": ["mind", "two", "decide", "unsure"]},
    {"ph": "Be on the same page", "tr": "Aynı fikirde olmak, hemfikir olmak", "k": ["page", "same", "agree"]},
    {"ph": "Left in the dark", "tr": "Habersiz bırakılmak, karanlıkta kalmak", "k": ["dark", "left", "know", "secret"]},
    {"ph": "See eye to eye", "tr": "Aynı fikirde olmak", "k": ["eye", "see", "agree"]},
    {"ph": "In hot water", "tr": "Başı dertte olmak, hapı yutmak", "k": ["hot", "water", "trouble"]},
    {"ph": "Get cold feet", "tr": "Son anda vazgeçmek, cesaretini kaybetmek", "k": ["cold", "feet", "scared", "cancel"]},
    {"ph": "Caught red-handed", "tr": "Suçüstü yakalanmak", "k": ["red", "hand", "catch", "crime"]},
    {"ph": "Spill the beans", "tr": "Baklayı ağzından çıkarmak, sırrı ifşa etmek", "k": ["spill", "bean", "secret"]},
    {"ph": "In deep water", "tr": "Başı büyük dertte olmak", "k": ["deep", "water", "trouble"]},
    {"ph": "At a crossroads", "tr": "Yol ayrımında olmak, karar aşamasında", "k": ["crossroad", "road", "decide"]},
    {"ph": "Under the weather", "tr": "Kendini keyifsiz veya hasta hissetmek", "k": ["weather", "sick", "ill"]},
    {"ph": "In a rut", "tr": "Monotonluğa kapılmak, yerinde saymak", "k": ["rut", "stuck", "boring"]},
    {"ph": "Blessing in disguise", "tr": "Şer gibi görünen hayır", "k": ["bless", "disguise", "good", "bad"]},
    {"ph": "Black sheep of the family", "tr": "Ailenin yüz karası (veya farklı olanı)", "k": ["black", "sheep", "family"]},
    {"ph": "Hard nut to crack", "tr": "Çetin ceviz, zorlu kişi/durum", "k": ["nut", "crack", "hard", "difficult"]},
    {"ph": "Piece of cake", "tr": "Çocuk oyuncağı (Çok kolay)", "k": ["piece", "cake", "easy"]},
    {"ph": "In a pickle", "tr": "Zor/Çıkmaza girmiş durumda olmak", "k": ["pickle", "trouble", "stuck"]},
    {"ph": "Sore thumb", "tr": "Göze batmak, sırıtmak", "k": ["sore", "thumb", "stand", "out"]},
    {"ph": "Needle in a haystack", "tr": "Samanlıkta iğne aramak", "k": ["needle", "haystack", "hard", "find"]},
    {"ph": "Snake in the grass", "tr": "Sinsi düşman", "k": ["snake", "grass", "enemy", "secret"]},
    {"ph": "Fly on the wall", "tr": "Gizlice dinleyen/izleyen kişi", "k": ["fly", "wall", "listen", "secret"]},
    {"ph": "Let the dust settle", "tr": "Ortalığın yatışmasını beklemek", "k": ["dust", "settle", "wait", "calm"]},
    {"ph": "Elephant in the room", "tr": "Herkesin bildiği ama konuşmadığı sorun", "k": ["elephant", "room", "problem", "ignore"]},
    {"ph": "In the same boat", "tr": "Aynı gemide olmak (Aynı kaderi paylaşmak)", "k": ["same", "boat", "situation"]},
    {"ph": "Fish out of water", "tr": "Sudan çıkmış balık gibi (Yabancı hissetmek)", "k": ["fish", "water", "strange"]},
    {"ph": "Apple of my eye", "tr": "Göz bebeğim", "k": ["apple", "eye", "love", "favorite"]},
    {"ph": "Hit the nail on the head", "tr": "Tam üstüne basmak, hedefi 12'den vurmak", "k": ["nail", "head", "hit", "exact"]},
    {"ph": "Let sleeping dogs lie", "tr": "Yatan köpeği uyandırma (Sorun çıkarma)", "k": ["sleep", "dog", "lie", "trouble"]},
    {"ph": "Hit the books", "tr": "İneklemek, çok ders çalışmak", "k": ["hit", "book", "study"]},
    {"ph": "Hit the sack", "tr": "Kafayı vurup yatmak", "k": ["hit", "sack", "sleep", "bed"]},
    {"ph": "Twist someone's arm", "tr": "Zorlamak, ağzından girip burnundan çıkmak", "k": ["twist", "arm", "force", "persuade"]},
    {"ph": "Stab someone in the back", "tr": "Sırtından bıçaklamak (İhanet etmek)", "k": ["stab", "back", "betray"]},
    {"ph": "Lose your touch", "tr": "Yeteneyini kaybetmek, paslanmak", "k": ["lose", "touch", "skill"]},
    {"ph": "Sit tight", "tr": "Yerinde durmak, sabırla beklemek", "k": ["sit", "tight", "wait"]},
    {"ph": "Pitch in", "tr": "İşe el atmak, katkıda bulunmak", "k": ["pitch", "help", "contribute"]},
    {"ph": "Go cold turkey", "tr": "Bir alışkanlığı bıçak gibi kesmek", "k": ["cold", "turkey", "quit", "habit"]},
    {"ph": "Face the music", "tr": "Yaptığının bedelini ödemek", "k": ["face", "music", "consequence"]},
    {"ph": "Ring a bell", "tr": "Tanıdık gelmek, bir şeyi çağrıştırmak", "k": ["ring", "bell", "familiar", "remind"]},
    {"ph": "Blow off steam", "tr": "Stres atmak, deşarj olmak", "k": ["blow", "steam", "relax", "anger"]},
    {"ph": "Cut to the chase", "tr": "Sadede gelmek, kısa kesmek", "k": ["cut", "chase", "point"]},
    {"ph": "Up in the air", "tr": "Havada/Askıda (Henüz belirsiz)", "k": ["up", "air", "uncertain", "decide"]},
    {"ph": "On the ball", "tr": "İşini bilen, açıkgöz, dikkatli", "k": ["ball", "alert", "sharp"]},
    {"ph": "Get over something", "tr": "Bir şeyi atlatmak, üstesinden gelmek", "k": ["get", "over", "recover"]},
    {"ph": "Look like a million dollars", "tr": "Muhteşem görünmek", "k": ["look", "million", "dollar", "buck", "great"]},
    {"ph": "Born with a silver spoon", "tr": "Ağzında gümüş kaşıkla doğmak (Zengin doğmak)", "k": ["born", "silver", "spoon", "rich"]},
    {"ph": "Rags to riches", "tr": "Sıfırdan zengin olmak", "k": ["rag", "rich", "poor", "money"]},
    {"ph": "Cost an arm and a leg", "tr": "Ateş pahası, servet ödemek", "k": ["cost", "arm", "leg", "expensive"]},
    {"ph": "Sticky fingers", "tr": "Eli uzun olmak (Hırsızlık huyu)", "k": ["sticky", "finger", "steal", "thief"]},
    {"ph": "Give a run for money", "tr": "Zorlamak, kök söktürmek", "k": ["run", "money", "challenge"]},
    {"ph": "Pony up", "tr": "Pamuk eller cebe (Borcunu ödemek)", "k": ["pony", "pay", "debt"]},
    {"ph": "Break even", "tr": "Ne kar ne zarar etmek", "k": ["break", "even", "profit", "loss"]},
    {"ph": "Break the bank", "tr": "Çok pahalı olmak, el yakmak", "k": ["break", "bank", "expensive"]},
    {"ph": "Closefisted", "tr": "Eli sıkı, cimri", "k": ["close", "fist", "cheap", "stingy"]},
    {"ph": "Go Dutch", "tr": "Hesabı alman usulü ödemek", "k": ["go", "dutch", "split", "bill"]},
    {"ph": "Midas touch", "tr": "Tuttuğu altın olmak (Çok başarılı)", "k": ["midas", "touch", "gold", "success"]},
    {"ph": "Living hand to mouth", "tr": "Ucu ucuna geçinmek", "k": ["live", "hand", "mouth", "poor"]},
    {"ph": "Make ends meet", "tr": "Kıt kanaat geçinmek, ay sonunu getirmek", "k": ["make", "end", "meet", "survive"]},
    {"ph": "Genuine as a three-dollar bill", "tr": "Sahte, güvenilmez", "k": ["genuine", "dollar", "bill", "fake"]},
    {"ph": "Rule of thumb", "tr": "Pratik kural, genel geçer yöntem", "k": ["rule", "thumb", "general"]},
    {"ph": "Keep your chin up", "tr": "Başını dik tut, metin ol", "k": ["keep", "chin", "up", "brave"]},
    {"ph": "Find your feet", "tr": "Ayak uydurmak, alışmak", "k": ["find", "feet", "adjust"]},
    {"ph": "Spice things up", "tr": "Renk katmak, heyecanlandırmak", "k": ["spice", "thing", "exciting"]},
    {"ph": "Cool as a cucumber", "tr": "Soğukkanlı, sakin", "k": ["cool", "cucumber", "calm"]},
    {"ph": "Couch potato", "tr": "Televizyon bağımlısı, miskin", "k": ["couch", "potato", "lazy", "tv"]},
    {"ph": "Bring home the bacon", "tr": "Evi geçindirmek, ekmek parası kazanmak", "k": ["bring", "home", "bacon", "money", "earn"]},
    {"ph": "Compare apples and oranges", "tr": "Elmayla armudu kıyaslamak", "k": ["compare", "apple", "orange", "different"]},
    {"ph": "Not my cup of tea", "tr": "Benim tarzım değil", "k": ["cup", "tea", "like", "style"]},
    {"ph": "Eat like a bird", "tr": "Kuş kadar yemek", "k": ["eat", "bird", "little"]},
    {"ph": "Eat like a horse", "tr": "Kıtlıktan çıkmış gibi yemek", "k": ["eat", "horse", "hungry"]},
    {"ph": "Butter someone up", "tr": "Yağ çekmek, pohpohlamak", "k": ["butter", "flatter"]},
    {"ph": "Food for thought", "tr": "Düşündürücü şey", "k": ["food", "thought", "think"]},
    {"ph": "Smart cookie", "tr": "Zeka küpü, akıllı", "k": ["smart", "cookie", "clever"]},
    {"ph": "Packed like sardines", "tr": "Balık istifi, tıkış tıkış", "k": ["pack", "sardine", "crowded"]},
    {"ph": "Bad apple", "tr": "Çürük elma (Kötü karakterli)", "k": ["bad", "apple", "person"]},
    {"ph": "Bread and butter", "tr": "Ekmek teknesi, geçim kaynağı", "k": ["bread", "butter", "job", "income"]},
    {"ph": "Buy a lemon", "tr": "Külüstür/Bozuk mal almak", "k": ["buy", "lemon", "car", "bad"]},
    {"ph": "Have a sweet tooth", "tr": "Tatlıya düşkün olmak", "k": ["sweet", "tooth", "candy"]},
    {"ph": "Storm is brewing", "tr": "Fırtına yaklaşıyor (Kötü bir şey olacak)", "k": ["storm", "brew", "trouble"]},
    {"ph": "Calm before the storm", "tr": "Fırtına öncesi sessizlik", "k": ["calm", "storm", "quiet"]},
    {"ph": "Weather a storm", "tr": "Badire atlatmak, zorluğa göğüs germek", "k": ["weather", "storm", "survive"]},
    {"ph": "When it rains, it pours", "tr": "Aksilikler üst üste gelir", "k": ["rain", "pour", "bad", "luck"]},
    {"ph": "Chasing rainbows", "tr": "Hayal peşinde koşmak", "k": ["chase", "rainbow", "dream"]},
    {"ph": "Rain or shine", "tr": "Ne olursa olsun, her koşulda", "k": ["rain", "shine", "matter"]},
    {"ph": "Under the sun", "tr": "Yeryüzündeki (her şey)", "k": ["under", "sun", "everything"]},
    {"ph": "Once in a blue moon", "tr": "Kırk yılda bir, çok nadir", "k": ["once", "blue", "moon", "rare"]},
    {"ph": "Every cloud has a silver lining", "tr": "Her şerde bir hayır vardır", "k": ["cloud", "silver", "lining", "hope"]},
    {"ph": "Rising tide lifts all boats", "tr": "Genel iyileşme herkese yarar", "k": ["rise", "tide", "boat", "economy"]},
    {"ph": "Pour oil on troubled waters", "tr": "Ortalığı yatıştırmak", "k": ["pour", "oil", "water", "calm"]},
    {"ph": "Make waves", "tr": "Ortalığı karıştırmak, ses getirmek", "k": ["make", "wave", "trouble"]},
    {"ph": "Go with the flow", "tr": "Akışına bırakmak", "k": ["go", "flow", "relax"]},
    {"ph": "Sail close to the wind", "tr": "Bıçak sırtında gitmek, risk almak", "k": ["sail", "wind", "risk", "dangerous"]},
    {"ph": "Make a mountain out of a molehill", "tr": "Pireyi deve yapmak", "k": ["mountain", "molehill", "exaggerate"]},
    {"ph": "Gain ground", "tr": "Mesafe katetmek, ilerlemek", "k": ["gain", "ground", "progress"]},
    {"ph": "Walking on air", "tr": "Sevinçten havalara uçmak", "k": ["walk", "air", "happy"]},
    {"ph": "Castle in the sky", "tr": "Boş hayal", "k": ["castle", "sky", "dream"]},
    {"ph": "Down to earth", "tr": "Ayakları yere basan, gerçekçi/mütevazı", "k": ["down", "earth", "real"]},
    {"ph": "Salt of the earth", "tr": "Dünya iyisi, muhterem", "k": ["salt", "earth", "good", "person"]},
    {"ph": "Tip of the iceberg", "tr": "Buzdağının görünen kısmı", "k": ["tip", "iceberg", "small", "part"]},
    {"ph": "Sell ice to Eskimos", "tr": "Tereciye tere satmak (İkna kabiliyeti yüksek)", "k": ["sell", "ice", "eskimo", "persuade"]},
    {"ph": "Bury your head in the sand", "tr": "Gerçekleri görmezden gelmek", "k": ["bury", "head", "sand", "ignore"]},
    {"ph": "Clear as mud", "tr": "Hiç anlaşılır değil, arap saçı", "k": ["clear", "mud", "confusing"]},
    {"ph": "Between a rock and a hard place", "tr": "İki arada bir derede, çıkmazda", "k": ["rock", "hard", "place", "stuck"]},
    {"ph": "Nip something in the bud", "tr": "Yılanın başını küçükken ezmek", "k": ["nip", "bud", "stop", "early"]},
    {"ph": "Barking up the wrong tree", "tr": "Yanlış kapıyı çalmak, yanılmak", "k": ["bark", "wrong", "tree", "mistake"]},
    {"ph": "Out of the woods", "tr": "Düzlüğe çıkmak, tehlikeyi atlatmak", "k": ["out", "wood", "safe"]},
    {"ph": "Cant see the forest for the trees", "tr": "Ayrıntıdan bütünü görememek", "k": ["forest", "tree", "detail", "big"]},
    {"ph": "Hold out an olive branch", "tr": "Zeytin dalı uzatmak (Barış istemek)", "k": ["hold", "olive", "branch", "peace"]},
    {"ph": "Beat around the bush", "tr": "Lafı gevelemek", "k": ["beat", "bush", "direct"]}
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
        # Aranan kelime deyimin icinde geciyor mu?
        if word in item['ph'].lower() or word in item['k']:
            found.append(f"🔹 *{item['ph']}*\n    _Anlamı: {item['tr']}_")
    return found[:3] # En fazla 3 sonuc

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    msg = (
        f"Merhaba {user}! 👋\n\n"
        "İstediğin kelimeyi bana yazabilirsin. Sana şunları sunabilirim:\n\n"
        "🇹🇷 Tam Çeviri\n"
        "📖 Sözlük Tanımı\n"
        "🎭 İlgili Deyimler\n"
        "🔊 Sesli Telaffuz\n\n"
        "_Hadi, bir kelime yazarak başlayalım!_ 👇"
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
    
    header = f"🔎 **Kelime:** `{word.capitalize()}`\n━━━━━━━━━━━━━━━━━━\n_Ne öğrenmek istersin?_"
    await update.message.reply_text(header, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("|")
    action, val = data[0], data[1]
    await query.answer()

    tr_to_en = get_translation(val, "tr", "en")
    en_to_tr = get_translation(val, "en", "tr")
    
    header = f"🔎 **Kelime:** `{val.capitalize()}`\n"
    content = ""

    # 1. CEVIRI
    if action == "c":
        # Eger ingilizceden turkceye cevirisi kelimenin kendisinden farkliysa
        # Demek ki kelime ingilizceymis ve cevrilmis.
        if en_to_tr != val: 
            content = (
                "🇹🇷 **Türkçe Anlamı**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"✨ `{en_to_tr.capitalize()}`"
            )
        else: # Degilse, kelime Turkceymis.
            content = (
                "🇬🇧 **İngilizce Karşılığı**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"✨ `{tr_to_en.capitalize()}`"
            )

    # 2. SES
    elif action == "s":
        speak_word = tr_to_en if en_to_tr == val else val
        try:
            tts = gTTS(text=speak_word, lang='en')
            tts.save(f"{val}.mp3")
            with open(f"{val}.mp3", 'rb') as audio: await context.bot.send_voice(query.message.chat_id, audio)
            os.remove(f"{val}.mp3"); return
        except: return

    # 3. DEYIMLER
    elif action == "i":
        search_word = val if en_to_tr != val else tr_to_en
        idioms = find_idioms(search_word)
        if idioms:
            content = "🎭 **İlgili Deyimler**\n━━━━━━━━━━━━━━━━━━\n" + "\n\n".join(idioms)
        else:
            content = "⚠️ _Bu kelimeyle ilgili kayıtlı bir deyim bulunamadı._"

    # 4. TANIM / ORNEK / ES ANLAM
    elif action in ["t", "o", "e"]:
        search_word = val if en_to_tr != val else tr_to_en
        try:
            if action == "e":
                r = requests.get(f"https://api.datamuse.com/words?rel_syn={search_word}")
                items = [f"`{i['word'].capitalize()}`" for i in r.json()[:5]]
                content = "🔗 **Eş Anlamlı Kelimeler**\n━━━━━━━━━━━━━━━━━━\n" + ", ".join(items) if items else "Bulunamadı."
            else:
                r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{search_word}")
                if r.status_code == 200:
                    d = r.json()[0]
                    if action == "t":
                        defi = d['meanings'][0]['definitions'][0]['definition']
                        content = f"📖 **İngilizce Tanım**\n━━━━━━━━━━━━━━━━━━\n_{defi}_"
                    else:
                        ex = "Örnek bulunamadı."
                        for m in d.get('meanings', []):
                            for de in m.get('definitions', []):
                                if de.get('example'): ex = de['example']; break
                        content = f"📝 **Örnek Cümle**\n━━━━━━━━━━━━━━━━━━\n_“{ex}”_"
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
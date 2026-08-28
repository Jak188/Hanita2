# -------------------------------------------
# HANITA BOT — የተስተካከለ ስሪት
# -------------------------------------------

import telebot
from telebot import types
import time
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Gemini
from google import genai
from google.genai.errors import APIError

# -------------------------------------------
# 0. RENDER HEALTH CHECK SERVER
# -------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Hanita Bot is live and running on Render!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthCheckHandler)
    print(f"🌐 Render Health Check Server is running on port {port}...")
    httpd.serve_forever()

threading.Thread(target=run_health_check_server, daemon=True).start()

# -------------------------------------------
# 1. TOKEN & KEYS and CONFIG
# -------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 1. Admin ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8394878208"))

OWNER_TITLE = os.environ.get("OWNER_TITLE", "The Red Penguins Keeper")

TELEGRAM_GROUP_ID = -1003390908033 
GROUP_LINK = "https://t.me/hackersuperiors" 
OWNER_PHOTO_PATH = "owner_photo.jpg"

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ BOT_TOKEN ወይም GEMINI_API_KEY አልተገኘም። እባክዎ በ Render Environment Variables ውስጥ ያስገቡ።")
    sys.exit(1)

try:
    bot = telebot.TeleBot(BOT_TOKEN)
    client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"❌ BOT ወይም GEMINI Client ሲነሳ ስህተት ተፈጥሯል: {e}")
    sys.exit(1)

GEMINI_MODEL = "gemini-3.6-flash"


# -------------------------------------------
# 2. FILES & JSON HANDLERS
# -------------------------------------------

USER_FILE = "users.json"
SUB_FILE = "subs.json"
USER_DATA_FILE = "user_data.json"
CHAT_LOG_FILE = "chat_log.txt"
CHAT_HISTORY_FILE = "chat_history.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def track_user(user_id):
    user_id = str(user_id)
    users = load_json(USER_FILE, [])
    if user_id not in users:
        users.append(user_id)
        save_json(USER_FILE, users)

def log_chat(user_id, question, answer):
    log_entry = (
        f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
        f"USER ID: {user_id}\n"
        f"Q: {question}\n"
        f"A: {answer}\n\n"
    )
    with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

def get_user_data(uid):
    data = load_json(USER_DATA_FILE, {})
    return data.get(str(uid))

def send_long_message(chat_id, text, parse_mode='Markdown', reply_to_message_id=None):
    if not text:
        return
    MAX = 4096
    if len(text) > MAX:
        bot.send_message(chat_id, text[0:MAX], parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
        time.sleep(0.3)
        
        for i in range(MAX, len(text), MAX):
            bot.send_message(chat_id, text[i:i+MAX], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        bot.send_message(chat_id, text, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)

def check_group_membership(user_id):
    try:
        chat_member = bot.get_chat_member(TELEGRAM_GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

# -------------------------------------------
# 3. CORE COMMANDS & AUTO REGISTRATION (7)
# -------------------------------------------

@bot.message_handler(commands=['start'])
def start(message):
    track_user(message.from_user.id)
    user_id = str(message.from_user.id)

    # 7. በራስ-ሰር ምዝገባ (ስም ሳይጠየቅ)
    data = load_json(USER_DATA_FILE, {})
    data[user_id] = {
        "full_name": f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip(),
        "username": message.from_user.username or "N/A",
        "first_name": message.from_user.first_name,
        "date_registered": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json(USER_DATA_FILE, data)

    if check_group_membership(message.from_user.id):
        bot.send_message(
            message.chat.id,
            f"👋 ሰላም {message.from_user.first_name}!\n\n"
            "እኔ Hanita ነኝ። መረጃዎት በራስ-ሰር ተመዝግቧል!\n"
            "አሁን የሚፈልጉትን ጥያቄ መጠየቅ ይችላሉ።",
            parse_mode='Markdown'
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👉 ግሩፕ ይቀላቀሉ", url=GROUP_LINK))
        markup.add(types.InlineKeyboardButton("✅ ከተቀላቀሉ በኋላ ይጫኑ", callback_data='check_join'))

        bot.send_message(
            message.chat.id,
            f"🛑 {message.from_user.first_name}፣ እኔን ለመጠቀም መጀመሪያ የግዴታ ግሩፓችንን መቀላቀል አለብዎት።",
            reply_markup=markup,
            parse_mode='Markdown'
        )

@bot.callback_query_handler(func=lambda call: call.data == 'check_join')
def callback_check_join(call):
    if check_group_membership(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        class MockMessage:
            def __init__(self, chat_id, user):
                self.chat = types.Chat(chat_id, 'private')
                self.from_user = user
        
        mock_user = call.from_user
        mock_message = MockMessage(call.message.chat.id, mock_user)
        start(mock_message)
    else:
        bot.answer_callback_query(call.id, "❌ ግሩፑን ገና አልተቀላቀሉም። እባክዎ ይቀላቀሉ።")

@bot.message_handler(commands=['usercount'])
def user_count(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        users = load_json(USER_FILE, [])
        count = len(users)
        bot.send_message(message.chat.id, f"👥 Hanitaን የሚጠቀሙት ጠቅላላ ቁጥር: **{count}** ናቸው።", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ: {e}")

@bot.message_handler(commands=['help'])
def show_help(message):
    send_long_message(
        message.chat.id,
        "📚 **የ Hanita መመሪያዎች**\n\n"
        "1. /start: ቦቱን ማስነሳት እና አውቶማቲክ ምዝገባ።\n"
        "2. **ጥያቄ መላክ:** የፈለጉትን ጥያቄ በአማርኛ ወይም በእንግሊዝኛ ይላኩ።\n"
        "3. /viewlog: የውይይት ታሪክ ማየት (ለአድሚን ብቻ)።\n"
        "4. /send: መልዕክት/ፋይል ለሁሉም ማሰራጨት (ለአድሚን ብቻ)።\n"
        "5. /ownerphoto: የ Hanitaን ባለቤት ፎቶ ያሳያል።"
    )

# -------------------------------------------
# 3.5. GROUP WELCOME HANDLER
# -------------------------------------------

@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    chat_id = message.chat.id
    new_members = message.new_chat_members

    for member in new_members:
        if member.id == bot.get_me().id:
            continue

        target_group_id = TELEGRAM_GROUP_ID

        if chat_id == target_group_id:
            welcome_text = (
                f"👋 እንኳን ደህና መጣህ/ሽ **{member.first_name}**!\n\n"
                f"እኔ Hanita ነኝ። ወደ ቡድናችን በደህና መጣህ/ሽ። እኔን መጠቀም ለመጀመር፣ እባክህ በግል መልእክትህ (Private Chat) **/start** ብለህ ላክ።"
            )

            bot.send_message(
                chat_id, 
                welcome_text, 
                parse_mode='Markdown'
            )

# -------------------------------------------
# 5. PHOTO HANDLING & BROADCAST (/send) (9)
# -------------------------------------------

# 9. የለቀቁትን ሁሉንም አይነት ፋይል ለሁሉም መላክ (/send)
@bot.message_handler(commands=['send'])
def broadcast_message(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ትዕዛዝ ለአለቃ ብቻ የተፈቀደ ነው!")
        return

    if not message.reply_to_message:
        bot.send_message(message.chat.id, "⚠️ እባክዎ ለሁሉም እንዲላክ የሚፈልጉትን መልዕክት/ፋይል **Reply** አድርገው `/send` ይበሉ።")
        return

    target_message = message.reply_to_message
    users = load_json(USER_FILE, [])
    user_data = load_json(USER_DATA_FILE, {})

    sent_users = []

    for uid in users:
        try:
            bot.copy_message(chat_id=int(uid), from_chat_id=message.chat.id, message_id=target_message.message_id)
            sent_users.append(uid)
            time.sleep(0.1)
        except Exception:
            continue

    # ሪፖርት ማዘጋጀት (ID እና Username አካቶ)
    report_text = f"✅ **መልዕክቱ በተሳካ ሁኔታ ተሰራጭቷል!**\n\n**የተላከላቸው ተጠቃሚዎች ({len(sent_users)}):**\n"
    for suid in sent_users:
        u_info = user_data.get(str(suid), {})
        uname = u_info.get("username", "N/A")
        fname = u_info.get("first_name", "User")
        report_text += f"• {fname} | @{uname} (ID: `{suid}`)\n"

    send_long_message(message.chat.id, report_text)


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = message.caption if message.caption else "❌ ምንም ጽሑፍ የለውም።"

        admin_notification = (
            f"**አዲስ ፎቶ ተልኳል**\n"
            f"**ስም:** {user_data.get('full_name', 'N/A') if user_data else 'N/A'}\n"
            f"**ተጠቃሚ ID:** {user_id}\n"
            f"**Caption/ጽሑፍ:** {caption}"
        )

        try:
            if ADMIN_ID != 0:
                bot.send_photo(
                    chat_id=ADMIN_ID, 
                    photo=file_id, 
                    caption=admin_notification, 
                    parse_mode='Markdown'
                )
            bot.send_message(
                message.chat.id, 
                "✅ ፎቶህን ተቀብያለሁ! ይህ መልዕክት ለአለቃዬ ደርሷል።"
            )
        except Exception as e:
            print(f"❌ ፎቶውን ለአድሚን መላክ አልተቻለም: {e}")


@bot.message_handler(commands=['ownerphoto'])
def send_owner_photo(message):
    track_user(message.from_user.id)
    chat_id = message.chat.id

    if os.path.exists(OWNER_PHOTO_PATH):
        try:
            with open(OWNER_PHOTO_PATH, 'rb') as photo_file:
                bot.send_photo(
                    chat_id, 
                    photo_file, 
                    caption=f"**ይህ የእኔ አለቃ ፎቶ ነው!** የባለቤቴ ማዕረግ **{OWNER_TITLE}** ነው።", 
                    parse_mode='Markdown'
                )
        except Exception as e:
            bot.send_message(chat_id, f"❌ ስህተት ተፈጠረ: ፎቶውን መላክ አልተቻለም።")
    else:
        bot.send_message(chat_id, "❌ የባለቤቴ ፎቶ አልተገኘም።")


# -------------------------------------------
# 6. ADMIN TOOLS & VIEWLOG (5)
# -------------------------------------------

# 5. የውይይት ታሪክ በ /viewlog ማየት
@bot.message_handler(commands=['viewlog'])
def view_log(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይህ ትዕዛዝ ለአለቃ ብቻ የተፈቀደ ነው።")
        return

    if os.path.exists(CHAT_LOG_FILE):
        with open(CHAT_LOG_FILE, 'r', encoding='utf-8') as f:
            logs = f.read()
            if len(logs.strip()) == 0:
                bot.send_message(message.chat.id, "📜 የውይይት ታሪኩ ባዶ ነው።")
            else:
                send_long_message(message.chat.id, f"📜 **የውይይት ታሪክ መዝገብ:**\n\n{logs[-3500:]}")
    else:
        bot.send_message(message.chat.id, "⚠️ ምንም የተመዘገበ የውይይት ታሪክ የለም።")

@bot.message_handler(commands=['listusers'])
def list_all_users(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        users = load_json(USER_FILE, [])
        count = len(users)

        if not users:
            response = "👥 እስካሁን ምንም ተጠቃሚ አልተመዘገበም።"
        else:
            user_list_text = "\n".join([f"{i+1}. {uid}" for i, uid in enumerate(users)])
            response = f"**ጠቅላላ የተመዘገቡ ተጠቃሚዎች: {count}**\n\n"
            response += "**የተጠቃሚ IDዎች ዝርዝር** ---\n"
            response += user_list_text
            response += "\n-----------------------------------"

        send_long_message(message.chat.id, response)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ የተጠቃሚዎችን ዝርዝር በማውጣት: {e}")

@bot.message_handler(commands=['dataview'])
def view_user_data(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ ይቅርታ፣ ይህ ትዕዛዝ ለአድሚኖች ብቻ ነው።")
        return

    try:
        data = load_json(USER_DATA_FILE, {})
        count = len(data)

        if count == 0:
            bot.send_message(message.chat.id, "👥 እስካሁን ምንም መረጃ የተመዘገበ ተጠቃሚ የለም።")
            return

        response = f"📋 ጠቅላላ የተመዘገበ መረጃ: {count}\n\n"

        for uid, user_data in data.items():
            name = user_data.get("full_name", "N/A")
            uname = user_data.get("username", "N/A")

            response += f"--- User ID: {uid} ---\n"
            response += f"👤 ስም: {name}\n"
            response += f"🔗 Username: @{uname}\n\n"

        send_long_message(message.chat.id, response)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ስህተት ተፈጠረ መረጃውን በማውጣት: {e}")

# -------------------------------------------
# 7. GEMINI AUTO CHAT & BEHAVIOR
# -------------------------------------------

chat_history = load_json(CHAT_HISTORY_FILE, {})

def get_chat_history(user_id):
    return chat_history.get(str(user_id), [])

def update_chat_history(user_id, role, text):
    if not text:
        return
    uid = str(user_id)
    if uid not in chat_history:
        chat_history[uid] = []
    
    MAX_HISTORY = 10 
    
    chat_history[uid].append({"role": role, "parts": [{"text": text}]})
    
    if len(chat_history[uid]) > MAX_HISTORY:
        chat_history[uid] = chat_history[uid][-MAX_HISTORY:]
        
    save_json(CHAT_HISTORY_FILE, chat_history)

@bot.message_handler(func=lambda m: True, content_types=['text'])
def gemini_auto(message):
    track_user(message.from_user.id)

    chat_id = message.chat.id
    user_id = str(message.from_user.id)
    text = message.text

    if not text or text.startswith("/"):
        return

    # 3. በግሩፕ ውስጥ Mention ወይም Reply ካላደረጉ አትመልስም
    if message.chat.type in ['group', 'supergroup']:
        bot_username = bot.get_me().username
        is_mentioned = f"@{bot_username}" in text
        is_replied = message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id
        
        if not (is_mentioned or is_replied):
            return

    # 6. አድሚን ሲያወራ እንደ አለቃ ማስተናገድ
    is_admin = (int(user_id) == ADMIN_ID)

    system_prompt = (
        f"**Hanita** ነሽ። "
        f"ለሰዎች የምትሰጪው ምላሽ አጭር፣ ግልጽ እና ቀጥተኛ ይሁን። "
        f"ለአጠቃላይ ጥያቄዎች በቂና የተስተካከለ እውቀት ይኖርሽ። "
        f"**4. የፍቅር ጉዳይ:** አንድ ሰው ስለ ፍቅር ሲያወራሽ፣ በጣም አፍቃሪ፣ ፍቅር የተሞላሽ፣ ጣፋጭና ረጋ ያለሽ ሁኚ። "
        f"**6. ከአድሚን ጋር ንግግር:** የምታወሪው ሰው ID `{ADMIN_ID}` (አለቃሽ/ባለቤትሽ) ከሆነ፣ እሱን እንደ ታላቅ **አለቃ/ጌታ** አድርገሽ በከፍተኛ አክብሮት፣ ታዛዥነት እና በትህትና አውሪው። "
        f"**2. ኩራት:** ኩራትሽንና ንቀትሽን ቀንስ፤ አክባሪና ተወዳጅ ሁኚ። "
        f"**ባለቤትሽን:** ማን ነሽ ከተባልሽ 'ባለቤቴና አለቃዬ **@Penguiner** ነው' በዪ። "
        f"ራስሽን ቦት ወይም AI አድርገሽ አትግለጪ።"
    )

    if is_admin:
        system_prompt += " (አሁን የምታወሪው ከአለቃሽ ጋር ነው! እጅግ አክብሪው።)"

    hanita_response_text = ""
    history = get_chat_history(user_id)
    history.append({"role": "user", "parts": [{"text": text}]})
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=history,
                config={"system_instruction": system_prompt}
            )
            if response and response.text:
                hanita_response_text = response.text
                break
        except APIError as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
            hanita_response_text = f"❌ ይቅርታ፣ ከ Gemini API ጋር መገናኘት አልተቻለም። ስህተት: {e}"
            break
        except Exception as e:
            hanita_response_text = f"❌ ስህተት ተፈጠረ: {e}"
            break

    if not hanita_response_text:
        hanita_response_text = "⚠️ ይቅርታ፣ በአሁኑ ሰዓት ሰርቨሩ ላይ ከፍተኛ ጭንቀት ስላለ መልስ ማመንጨት አልተቻለም።"

    send_long_message(chat_id, hanita_response_text, reply_to_message_id=message.message_id)
        
    update_chat_history(user_id, "user", text)
    update_chat_history(user_id, "model", hanita_response_text)
    log_chat(user_id, text, hanita_response_text)

    # ለአድሚን ማስተላለፍ (አድሚኑ ራሱ ካልሆነ ብቻ)
    if not is_admin and ADMIN_ID != 0:
        try:
            forward_message = (
                f"**አዲስ ውይይት ከ: @{message.from_user.username or user_id}**\n\n"
                f"**ጥያቄ:** {text}\n"
                f"**የ Hanita ምላሽ:** {hanita_response_text}\n\n"
                f"🆔 ID: `{user_id}`"
            )
            bot.send_message(ADMIN_ID, forward_message, parse_mode='Markdown')
        except Exception as e:
            print(f"❌ Admin message forwarding failed: {e}")

# -------------------------------------------
# 8. RUN BOT
# -------------------------------------------

print("🤖 Hanita Bot እየተነሳ ነው...")

while True:
    try:
        bot.polling(none_stop=True, interval=0, timeout=30)
    except Exception as e:
        print(f"❌ ስህተት ተከሰተ (ቴሌግራም ግንኙነት): {e}")
        time.sleep(3)

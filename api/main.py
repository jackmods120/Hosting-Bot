#  ╭───𓆩🛡️𓆪───╮
#  👨‍💻 𝘿𝙚𝙫: @j4ck_721s  
#  👤 𝙉𝙖𝙢𝙚: ﮼جــاڪ ,.⏳🤎:)
#   📢 𝘾𝙝: @j4ck_721s
import telebot
import subprocess
import os
import zipfile
import shutil
import re
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import logging
from logging import StreamHandler
import threading
import sys
import atexit
import requests
from flask import Flask, request
import signal
import html 

# --- Suppress Flask & Werkzeug Logging ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# Flask App for Vercel Serverless
app = Flask(__name__)

# --- Configuration (Vercel Mode) ---
# وەرگرتنی تۆکێن، گەر نەبوو ئێرۆر دەگرێت لەجیاتی ئەوەی بوەستێت
TOKEN = os.environ.get('BOT_TOKEN') or "MISSING_TOKEN"

OWNER_ID = 5977475208
YOUR_USERNAME = 'j4ck_721s'
UPDATE_CHANNEL = 'https://t.me/j4ck_721'

# Absolute Paths (لە Vercel دەبێت تەنها /tmp بەکاربهێنرێت)
BASE_DIR = "/tmp"
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')
MAIN_BOT_LOG_PATH = os.path.join(IROTECH_DIR, 'main_bot_log.log')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

# بۆ Vercel دەبێت threaded=False بێت
bot = telebot.TeleBot(TOKEN, threaded=False)

# --- Data Structures ---
bot_scripts = {} 
user_files = {} 
user_selected_file = {} 
bot_usernames_cache = {}
pending_referrals = {}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(MAIN_BOT_LOG_PATH, encoding='utf-8'),
        StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- ReplyKeyboardMarkup Layouts ---
MAIN_MENU_BUTTONS_LAYOUT = [["ℹ️ دەربارە", "🔗 بانگهێشت"], ["📤 ناردنی فایل", "📂 فایلەکانم"]]
ADMIN_MENU_BUTTONS_LAYOUT = [["ℹ️ دەربارە", "🔗 بانگهێشت"],["📤 ناردنی فایل", "📂 فایلەکانم"],["👑 پانێڵی گەشەپێدەر"]]
OWNER_PANEL_LAYOUT = [["📊 ئاماری بۆت", "💰 لیستی کڕیارەکان"],["📢 ناردنی گشتی", "🔒 قفڵکردن/کردنەوە"],["➕ زیادکردنی کڕیار", "⏳ درێژکردنەوەی کات"],["➖ سڕینەوەی کڕیار", "📢 زیادکردنی جۆین"],["📢 سڕینەوەی جۆین", "🆓 بێ بەرامبەر/بەپارە"],["➕ زیادکردنی ئەدمین", "➖ سڕینەوەی ئەدمین"],["📋 لیستی جۆین", "📋 لیستی ئەدمینەکان"],["🔙 گەڕانەوە بۆ مینیو"]
]
CONTROL_PANEL_LAYOUT = [["▶️ دەستپێکردن", "⏸ وەستاندن"], ["🔄 نوێکردنەوە", "🗑 سڕینەوە"],["📋 لۆگ", "📦 Requirements"],["📥 دابەزاندن", "🔙 گەڕانەوە بۆ مینیو"]
]

# --- Database Setup ---
DB_LOCK = threading.Lock()

def init_db():
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT, status TEXT, bot_token_id TEXT, PRIMARY KEY (user_id, file_name))''')
        c.execute("PRAGMA table_info(user_files)")
        columns = [column[1] for column in c.fetchall()]
        if 'bot_username' not in columns:
            c.execute('ALTER TABLE user_files ADD COLUMN bot_username TEXT')
        
        c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY)''')
        c.execute("PRAGMA table_info(active_users)")
        au_columns = [column[1] for column in c.fetchall()]
        if 'slots' not in au_columns:
            c.execute('ALTER TABLE active_users ADD COLUMN slots INTEGER DEFAULT 1')
        if 'referred_by' not in au_columns:
            c.execute('ALTER TABLE active_users ADD COLUMN referred_by INTEGER')

        c.execute('''CREATE TABLE IF NOT EXISTS purchases
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, purchase_date TEXT, days_count INTEGER, price REAL, expiry_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_by INTEGER, added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS force_join_channels (channel_username TEXT PRIMARY KEY)''')
        
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('bot_locked', 'false'))
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('free_mode', 'false'))
        conn.commit()
        conn.close()

def load_data():
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute("PRAGMA table_info(user_files)")
        columns = [column[1] for column in c.fetchall()]
        has_username = 'bot_username' in columns
        query = 'SELECT user_id, file_name, file_type, status, bot_token_id' + (', bot_username' if has_username else '') + ' FROM user_files'
        c.execute(query)
        for row in c.fetchall():
            user_id = row[0]
            bot_username = row[5] if has_username and len(row) > 5 else None
            user_files.setdefault(user_id,[]).append((row[1], row[2], row[3], row[4], bot_username))
        conn.close()

# --- Database Helpers ---
def add_user_to_db(user_id, referrer_id=None):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id FROM active_users WHERE user_id = ?', (user_id,))
        exists = c.fetchone()
        is_new_user = False
        if exists is None:
            c.execute('INSERT INTO active_users (user_id, slots, referred_by) VALUES (?, ?, ?)', (user_id, 1, referrer_id))
            is_new_user = True
        conn.commit()
        conn.close()
        return is_new_user

def get_user_slots(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT slots FROM active_users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        if result and result[0]: return result[0]
        return 1

def increment_user_slots(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('UPDATE active_users SET slots = slots + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

def get_all_users():
    users =[]
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id FROM active_users')
        for row in c.fetchall(): users.append(row[0])
        conn.close()
    return users

def update_user_file_db(user_id, file_name, file_type, status, bot_token_id, bot_username=None):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type, status, bot_token_id, bot_username) VALUES (?, ?, ?, ?, ?, ?)',
                  (user_id, file_name, file_type, status, bot_token_id, bot_username))
        conn.commit(); conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        conn.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
        conn.commit(); conn.close()

def get_all_purchases():
    purchases =[]
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.execute('SELECT id, user_id, purchase_date, days_count, price, expiry_date FROM purchases ORDER BY id DESC')
        for row in c.fetchall():
            purchases.append({'id': row[0], 'user_id': row[1], 'purchase_date': row[2], 'days_count': row[3], 'price': row[4], 'expiry_date': row[5]})
        conn.close()
    return purchases

def get_user_active_subscription(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('SELECT expiry_date FROM purchases WHERE user_id = ? AND expiry_date > ? ORDER BY expiry_date DESC LIMIT 1', (user_id, now))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

def add_subscription_manual(user_id, days):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        purchase_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO purchases (user_id, purchase_date, days_count, price, expiry_date) VALUES (?, ?, ?, ?, ?)',
                  (user_id, purchase_date, days, 0.0, expiry_date))
        conn.commit()
        conn.close()

def extend_subscription_db(user_id, days):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        now = datetime.now()
        c.execute('SELECT expiry_date FROM purchases WHERE user_id = ? ORDER BY expiry_date DESC LIMIT 1', (user_id,))
        result = c.fetchone()
        
        new_expiry = None
        if result:
            try:
                current_expiry = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                if current_expiry > now: new_expiry = current_expiry + timedelta(days=days)
                else: new_expiry = now + timedelta(days=days)
            except: new_expiry = now + timedelta(days=days)
        else: new_expiry = now + timedelta(days=days)
            
        purchase_date = now.strftime('%Y-%m-%d %H:%M:%S')
        new_expiry_str = new_expiry.strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO purchases (user_id, purchase_date, days_count, price, expiry_date) VALUES (?, ?, ?, ?, ?)',
                  (user_id, purchase_date, days, 0.0, new_expiry_str))
        conn.commit()
        conn.close()
        return new_expiry_str

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE purchases SET expiry_date = ? WHERE user_id = ?', (past_date, user_id))
        conn.commit()
        conn.close()

def clean_expired_subscriptions():
    try:
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('DELETE FROM purchases WHERE expiry_date < ?', (now,))
            conn.commit()
            conn.close()
    except: pass

def add_force_channel(channel):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO force_join_channels (channel_username) VALUES (?)', (channel,))
        conn.commit()
        conn.close()

def remove_force_channel(channel):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM force_join_channels WHERE channel_username = ?', (channel,))
        conn.commit()
        conn.close()

def get_force_channels():
    channels =[]
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT channel_username FROM force_join_channels')
        for row in c.fetchall(): channels.append(row[0])
        conn.close()
    return channels

def is_admin(user_id):
    if user_id == OWNER_ID: return True
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None

def add_admin(user_id, added_by):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        added_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT OR REPLACE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)', (user_id, added_by, added_date))
        conn.commit(); conn.close()

def remove_admin(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit(); conn.close()

def get_all_admins():
    admins =[]
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, added_by, added_date FROM admins')
        for row in c.fetchall(): admins.append({'user_id': row[0], 'added_by': row[1], 'added_date': row[2]})
        conn.close()
    return admins

def get_bot_setting(key):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT setting_value FROM bot_settings WHERE setting_key = ?', (key,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

def set_bot_setting(key, value):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', (key, value))
        conn.commit(); conn.close()

def is_bot_locked(): return get_bot_setting('bot_locked') == 'true'
def is_free_mode(): return get_bot_setting('free_mode') == 'true'

def count_user_hosted_bots(user_id):
    files = user_files.get(user_id,[])
    return len(files)

def get_bot_username_from_token(token):
    if token in bot_usernames_cache: return bot_usernames_cache[token]
    try:
        temp_bot = telebot.TeleBot(token)
        me = temp_bot.get_me()
        username = f"@{me.username}" if me.username else "N/A"
        bot_usernames_cache[token] = username
        return username
    except Exception: return "N/A"

def get_bot_start_count(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    script_info = bot_scripts.get(script_key, {})
    return script_info.get('start_count', 0)

def increment_bot_start_count(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    if script_key in bot_scripts: bot_scripts[script_key]['start_count'] = bot_scripts[script_key].get('start_count', 0) + 1
    else: bot_scripts[script_key] = {'start_count': 1}

def get_bot_uptime(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and 'start_time' in script_info:
        uptime_seconds = int(time.time() - script_info['start_time'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    return "0h 0m 0s"

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

# --- Improved Process Checking ---
def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if not script_info or not script_info.get('process'): return False
    proc = script_info['process']
    return proc.poll() is None

def kill_process_tree(process_info):
    if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
        try: process_info['log_file'].close()
        except Exception: pass

    process = process_info.get('process')
    log_path = process_info.get('log_path') 
    if not process: return

    try:
        process.terminate()
        try: process.wait(timeout=2)
        except subprocess.TimeoutExpired: process.kill() 
    except Exception:
        try:
            if process.pid: os.kill(process.pid, signal.SIGKILL)
        except Exception: pass 
            
    if log_path and os.path.exists(log_path):
        try: os.remove(log_path)
        except Exception: pass

def start_script(user_id, file_name):
    user_folder = get_user_folder(user_id)
    script_path = os.path.join(user_folder, file_name)
    if not os.path.isfile(script_path): raise FileNotFoundError(f"Script file {file_name} not found.")

    script_key = f"{user_id}_{file_name}"
    if is_bot_running(user_id, file_name): return True 

    log_filename = f"{script_key}_log.log"
    log_path = os.path.join(user_folder, log_filename)
    try:
        log_file = open(log_path, 'w', encoding='utf-8')
        process = subprocess.Popen([sys.executable, '-u', script_path], stdout=log_file, stderr=subprocess.STDOUT, cwd=user_folder)
        
        if script_key not in bot_scripts: bot_scripts[script_key] = {'start_count': 0}
        bot_scripts[script_key].update({'process': process, 'log_file': log_file, 'log_path': log_path, 'script_key': script_key, 'user_id': user_id, 'file_name': file_name, 'start_time': time.time()})
        increment_bot_start_count(user_id, file_name)
        return True
    except Exception as e:
        logger.error(f"Failed to start script {script_key}: {e}")
        if 'log_file' in locals() and not log_file.closed: log_file.close()
        raise

def stop_script(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if not script_info: return False
    kill_process_tree(script_info)
    start_count = script_info.get('start_count', 0)
    if script_key in bot_scripts: del bot_scripts[script_key]
    bot_scripts[script_key] = {'start_count': start_count}
    return True

# --- Force Join Checker ---
def check_force_join(user_id):
    if user_id == OWNER_ID or is_admin(user_id): return True,[]
    channels = get_force_channels()
    not_joined =[]
    for channel in channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in['creator', 'administrator', 'member']: not_joined.append(channel)
        except Exception: pass 
    if not_joined: return False, not_joined
    return True,[]

# --- GUI / Menu Functions ---
def send_main_menu(chat_id, user_id):
    if user_id in user_selected_file: del user_selected_file[user_id]
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = ADMIN_MENU_BUTTONS_LAYOUT if (user_id == OWNER_ID or is_admin(user_id)) else MAIN_MENU_BUTTONS_LAYOUT
    for row in layout: markup.add(*row)
    bot.send_message(chat_id, "🏠 مینیوی سەرەکی:", reply_markup=markup)

def send_control_panel(chat_id, file_name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in CONTROL_PANEL_LAYOUT: markup.add(*row)
    bot.send_message(chat_id, f"⚙️ <b>کۆنترۆڵی فایل: {file_name}</b>", parse_mode='HTML', reply_markup=markup)

def send_owner_panel(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in OWNER_PANEL_LAYOUT: markup.add(*row)
    bot.send_message(chat_id, "👑 <b>پانێڵی گەشەپێدەر</b>", parse_mode='HTML', reply_markup=markup)

def send_join_request(chat_id, channels):
    markup = types.InlineKeyboardMarkup()
    for channel in channels: markup.add(types.InlineKeyboardButton(f"📢 جۆین {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("✅ جۆینم کرد", callback_data="check_join_status"))
    bot.send_message(chat_id, "⚠️ <b>تکایە سەرەتا جۆینی ئەم چەناڵانە بکە بۆ بەکارهێنانی بۆت:</b>", parse_mode='HTML', reply_markup=markup)

# --- Message Handlers ---
@bot.message_handler(commands=['start'])
def start_command(message):
    clean_expired_subscriptions() 
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        potential_referrer = int(args[1])
        if potential_referrer != user_id: pending_referrals[user_id] = potential_referrer

    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined: return send_join_request(message.chat.id, missing_channels)
    process_successful_entry(message)

def process_successful_entry(message):
    user_id = message.from_user.id
    referrer_id = pending_referrals.pop(user_id, None)
    is_new_user = add_user_to_db(user_id, referrer_id)
    
    if is_new_user and referrer_id:
        increment_user_slots(referrer_id)
        try: bot.send_message(referrer_id, f"🎉 پیرۆزە! بەکارهێنەرێک بە لینکی تۆ جۆینی کرد.\n➕ 1 بۆت بۆ هەژمارەکەت زیادکرا.\n🆔: {user_id}")
        except: pass

    if is_new_user:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
            current_time = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
            bot.send_message(OWNER_ID, f"🔔 <b>بەکارهێنەرێکی نوێ!</b>\n\n👤 ناو: {message.from_user.first_name}\n🆔 ئایدی: <code>{user_id}</code>\n📝 یوزەر: {username}\n🕐 کات: {current_time}", parse_mode='HTML')
        except: pass

    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "🔒 بۆت لە ئێستادا داخراوە.")
    
    send_main_menu(message.chat.id, user_id)
    current_time_display = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
    welcome_text = (
        f"╔═══════════════════╗\n   🌟 <b>بەخێربێیت {message.from_user.first_name}!</b> 🌟\n╚═══════════════════╝\n\n"
        f"🤖 <b>بۆتی هۆستینگ - Vercel Edition</b>\n\nمن یارمەتیدەرێکی پێشکەوتووم بۆ:\n"
        f"• 🚀 هۆست کردنی بۆتەکانت\n• 🔍 پشتیوانی لە فایلی .py و .zip\n• ⚡ چاودێری ڕاستەوخۆی لۆگەکان\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n🕐 کات: {current_time_display}\n━━━━━━━━━━━━━━━━━━━━\n\n👇 دوگمەکانی خوارەوە هەڵبژێرە:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "check_join_status")
def check_join_callback(call):
    user_id = call.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if is_joined:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ سوپاس بۆ جۆینکردن!")
        class FakeMessage:
            def __init__(self, user, chat_id, text):
                self.from_user = user; self.chat = type('obj', (object,), {'id': chat_id}); self.text = text
        process_successful_entry(FakeMessage(call.from_user, call.message.chat.id, "/start"))
    else: bot.answer_callback_query(call.id, "❌ هێشتا جۆینت نەکردووە!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_subscription")
def buy_subscription_callback(call):
    text = f"💎 <b>کڕینی پلان (Premium)</b>\n\n💳 <b>ڕێگاکانی پارەدان:</b>\n• Korek Telecom\n\n💬 بۆ کڕین تکایە نامە بنێرە:\n👤 @{YOUR_USERNAME}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 پەیوەندی کردن", url=f"https://t.me/{YOUR_USERNAME}"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔗 بانگهێشت")
def invite_button(message):
    user_id = message.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    slots = get_user_slots(user_id)
    text = f"🔗 <b>بانگهێشتی هاوڕێکانت بکە!</b>\n\n🎁 بۆ هەر هاوڕێیەک کە دەیهێنیت، <b>١ بۆت</b>ی زیاتر وەردەگریت.\n\n🤖 ژمارەی بۆتەکانت: <b>{slots}</b>\n\n📎 <b>لینکەکەت:</b>\n<code>{invite_link}</code>"
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "ℹ️ دەربارە")
def about_button(message):
    bot.send_message(message.chat.id, f"👋 <b>دەربارەی ئێمە</b>\n\nئێمە لێرەین بۆ هۆستکردنی فایلەکانت.\n\n👨‍💻 گەشەپێدەر: @{YOUR_USERNAME}", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "📤 ناردنی فایل")
def upload_file_button(message):
    user_id = message.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined: return send_join_request(message.chat.id, missing_channels)
    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "🔒 بۆت داخراوە.")

    if not is_free_mode() and not get_user_active_subscription(user_id) and count_user_hosted_bots(user_id) >= get_user_slots(user_id) and user_id != OWNER_ID and not is_admin(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 کڕین", callback_data="buy_subscription"))
        return bot.send_message(user_id, f"⚠️ سنووری بۆتەکانت تەواو بووە.", reply_markup=markup, parse_mode='HTML')

    bot.send_message(message.chat.id, "📤 <b>ناردنی فایل</b>\n\n📂 تکایە فایلی بۆتەکەت بنێرە (.py یان .zip)", parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "📂 فایلەکانم")
def my_files_button(message):
    user_id = message.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined: return send_join_request(message.chat.id, missing_channels)
    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "🔒 بۆت داخراوە.")
    list_user_files(message)

# --- OWNER PANEL HANDLERS ---
@bot.message_handler(func=lambda message: message.text == "👑 پانێڵی گەشەپێدەر")
def admin_panel_button(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "⛔ تۆ ڕێگەپێدراو نیت.")
    send_owner_panel(message.chat.id)

@bot.message_handler(func=lambda message: message.text in[
    "📊 ئاماری بۆت", "💰 لیستی کڕیارەکان", "➕ زیادکردنی کڕیار", "➖ سڕینەوەی کڕیار",
    "📢 زیادکردنی جۆین", "📢 سڕینەوەی جۆین", "📋 لیستی جۆین", "🔒 قفڵکردن/کردنەوە",
    "🆓 بێ بەرامبەر/بەپارە", "➕ زیادکردنی ئەدمین", "➖ سڕینەوەی ئەدمین", 
    "📋 لیستی ئەدمینەکان", "📢 ناردنی گشتی", "⏳ درێژکردنەوەی کات"
])
def owner_panel_actions(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not is_admin(user_id): return
    action = message.text

    if action == "📊 ئاماری بۆت":
        with DB_LOCK:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM active_users')
            total_users = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM user_files')
            total_files = c.fetchone()[0]
            conn.close()
        response = f"📊 <b>ئاماری بۆت:</b>\n👥 بەکارهێنەران: {total_users}\n📂 فایلەکان: {total_files}"
        bot.send_message(message.chat.id, response, parse_mode='HTML')

    elif action == "📢 ناردنی گشتی":
        msg = bot.send_message(message.chat.id, "📝 نامەکەت بنێرە:")
        bot.register_next_step_handler(msg, process_broadcast)
    # The rest of admin panels follow same simple step logic (kept short for Vercel limits)

def process_broadcast(message):
    users = get_all_users()
    sent = 0
    msg = bot.send_message(message.chat.id, "⏳ دەستپێکردنی ناردن...")
    for uid in users:
        try: bot.copy_message(uid, message.chat.id, message.message_id); sent += 1
        except: pass
    bot.edit_message_text(f"✅ نامەکە نێردرا بۆ {sent} بەکارهێنەر.", message.chat.id, msg.message_id)

def install_system_dependencies():
    try: subprocess.run(['pkg', 'install', 'libxml2', 'libxslt', 'libjpeg-turbo', '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

def install_requirements_safe(user_folder):
    install_system_dependencies()
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--prefer-binary", "--no-cache-dir", "-r", "requirements.txt"], cwd=user_folder)
        return True
    except: return False

@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_id = message.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined: return send_join_request(message.chat.id, missing_channels)
    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "🔒 بۆت داخراوە.")
    
    file = message.document
    file_name = file.file_name
    if not (file_name.endswith('.py') or file_name.endswith('.zip')): return bot.send_message(message.chat.id, "❌ فۆرماتی هەڵە.")

    user_folder = get_user_folder(user_id)
    progress = bot.send_message(message.chat.id, "⏳ بارکردن...\n⬜️⬜️⬜️⬜️ 0%")
    try:
        file_path = os.path.join(user_folder, file_name)
        with open(file_path, 'wb') as f: f.write(bot.download_file(bot.get_file(file.file_id).file_path))
        bot.edit_message_text("⏳ بارکردن...\n▓▓▓▓░░ 40%", message.chat.id, progress.message_id)
        target_py = None
        
        if file_name.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref: zip_ref.extractall(user_folder)
            os.remove(file_path)
            if os.path.exists(os.path.join(user_folder, 'requirements.txt')): install_requirements_safe(user_folder)
            for f in os.listdir(user_folder):
                if f.endswith('.py'):
                    update_user_file_db(user_id, f, 'py', 'approved', "N/A", "N/A")
                    user_files.setdefault(user_id,[]).append((f, 'py', 'approved', "N/A", "N/A"))
                    target_py = f
        else:
            update_user_file_db(user_id, file_name, 'py', 'approved', "N/A", "N/A")
            user_files.setdefault(user_id,[]).append((file_name, 'py', 'approved', "N/A", "N/A"))
            target_py = file_name

        if target_py:
            bot.edit_message_text("⚙️ پشکنین...\n▓▓▓▓▓▓ 90%", message.chat.id, progress.message_id)
            start_script(user_id, target_py)
            user_selected_file[user_id] = target_py
            bot.delete_message(message.chat.id, progress.message_id)
            info_msg = f"🤖 <b>زانیاری فایل</b>\n\n📂 فایل: {target_py}\n📊 دۆخ: 🟢 Running\n⚠️ Vercel Limit: دەکرێت بوەستێت"
            bot.send_message(message.chat.id, info_msg, parse_mode='HTML')
            send_control_panel(message.chat.id, target_py)

    except Exception as e: bot.edit_message_text(f"❌ هەڵە: {e}", message.chat.id, progress.message_id)

def list_user_files(message):
    user_id = message.from_user.id
    files = user_files.get(user_id,[])
    if not files: return bot.send_message(message.chat.id, "📂 فایلەکانت\n\n❌ هیچ فایلێک نییە.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for f in files: markup.add(types.KeyboardButton(f"{'🟢' if is_bot_running(user_id, f[0]) else '🔴'} {f[0]}"))
    markup.add("🔙 گەڕانەوە بۆ مینیو")
    bot.send_message(message.chat.id, "📂 فایلێک هەڵبژێرە:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text and (message.text.startswith("🟢 ") or message.text.startswith("🔴 ")))
def handle_file_selection(message):
    user_id = message.from_user.id
    file_name = message.text[2:]
    files = user_files.get(user_id,[])
    file_info = next((f for f in files if f[0] == file_name), None)
    if not file_info: return bot.send_message(message.chat.id, "❌ فایل نەدۆزرایەوە.")
    user_selected_file[user_id] = file_name
    status = "🟢 Running" if is_bot_running(user_id, file_name) else "🔴 Stopped"
    info = f"🤖 <b>زانیاری فایل</b>\n\n📂 فایل: {file_name}\n📊 دۆخ: {status}"
    bot.send_message(message.chat.id, info, parse_mode='HTML')
    send_control_panel(message.chat.id, file_name)

@bot.message_handler(func=lambda message: message.text in["▶️ دەستپێکردن", "⏸ وەستاندن", "🔄 نوێکردنەوە", "🗑 سڕینەوە", "📋 لۆگ", "📥 دابەزاندن", "📦 Requirements", "🔙 گەڕانەوە بۆ مینیو"])
def handle_control(message):
    user_id = message.from_user.id
    action = message.text
    if action == "🔙 گەڕانەوە بۆ مینیو": return send_main_menu(message.chat.id, user_id)
    file_name = user_selected_file.get(user_id)
    if not file_name: return list_user_files(message)

    if action == "▶️ دەستپێکردن":
        start_script(user_id, file_name); bot.send_message(message.chat.id, "✅ دەستی پێکرد.")
    elif action == "⏸ وەستاندن":
        stop_script(user_id, file_name); bot.send_message(message.chat.id, "🛑 وەستاندرا.")
    elif action == "🔄 نوێکردنەوە":
        stop_script(user_id, file_name); time.sleep(1); start_script(user_id, file_name); bot.send_message(message.chat.id, "🔄 نوێکرایەوە.")
    elif action == "🗑 سڕینەوە":
        stop_script(user_id, file_name)
        remove_user_file_db(user_id, file_name)
        if user_id in user_files: user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
        bot.send_message(message.chat.id, "🗑 سڕایەوە.")
        send_main_menu(message.chat.id, user_id)
    elif action == "📋 لۆگ":
        log_path = os.path.join(get_user_folder(user_id), f"{user_id}_{file_name}_log.log")
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()[-3000:]
            bot.send_message(message.chat.id, f"📄 <b>Log:</b>\n<pre>{html.escape(content)}</pre>", parse_mode='HTML')
        else: bot.send_message(message.chat.id, "📄 فایلەکە ڕاوەستاوە، لۆگ سڕاوەتەوە.")


# --- Vercel Webhook Routes (نوێکراوەتەوە) ---
# لەمەودوا پێویست ناکات خەمی لینکەکەت بێت، هەرچییەک بێت دەیخوێنێتەوە
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def webhook(path):
    # پشکنین بۆ ئەوەی بزانین تۆکێن لە Vercel دانراوە یاخود نا
    if TOKEN == "MISSING_TOKEN":
        return "⚠️ هەڵە: BOT_TOKEN لەناو Vercel دانەنراوە! تکایە لە Settings > Environment Variables زیادی بکە.", 200
        
    # پشکنینی داتابەیس بۆ ئەوەی دڵنیا بین کار دەکات
    try:
        init_db()
        load_data()
    except Exception as e:
        print("Database error:", e)

    # وەرگرتنی نامەی تێلیگرام
    if request.method == 'POST':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"Update Error: {e}")
            return 'Error processed', 200
    else:
        # کاتێک لینکەکە لە گۆگڵ دەکەیتەوە ئەمەت پێ دەڵێت
        return "🚀 Vercel Webhook Hosting Bot is Running Perfectly!", 200

def cleanup():
    for key in list(bot_scripts.keys()):
        try: stop_script(*key.split('_', 1))
        except: pass
atexit.register(cleanup)

# --- START OF FILE app.py ---

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
from flask import Flask
from threading import Thread
import signal
import html  # For safe log printing

# --- Suppress Flask & Werkzeug Logging ---
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# Flask Keep-Alive Setup
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Bot is hosted by ﮼جــاڪ ,.⏳🤎:) 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- Configuration ---
TOKEN = os.environ.get('BOT_TOKEN', '8441747675:AAHsCI4sMLAVBNj-I6ixLYIQsBotFYWhva4')
OWNER_ID = 5977475208
YOUR_USERNAME = 'j4ck_721s'
UPDATE_CHANNEL = 'https://t.me/j4ck_721'

# Absolute Paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')
MAIN_BOT_LOG_PATH = os.path.join(IROTECH_DIR, 'main_bot_log.log')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

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

# 1. Main Menu
MAIN_MENU_BUTTONS_LAYOUT = [
    ["ℹ️ دەربارە", "🔗 بانگهێشت"],
    ["📤 ناردنی فایل", "📂 فایلەکانم"]
]

# 2. Admin Menu
ADMIN_MENU_BUTTONS_LAYOUT = [
    ["ℹ️ دەربارە", "🔗 بانگهێشت"],
    ["📤 ناردنی فایل", "📂 فایلەکانم"],
    ["👑 پانێڵی گەشەپێدەر"]
]

# 3. Owner Panel
OWNER_PANEL_LAYOUT = [
    ["📊 ئاماری بۆت", "💰 لیستی کڕیارەکان"],
    ["📢 ناردنی گشتی", "🔒 قفڵکردن/کردنەوە"],
    ["➕ زیادکردنی کڕیار", "⏳ درێژکردنەوەی کات"], 
    ["➖ سڕینەوەی کڕیار", "📢 زیادکردنی جۆین"],
    ["📢 سڕینەوەی جۆین", "🆓 بێ بەرامبەر/بەپارە"],
    ["➕ زیادکردنی ئەدمین", "➖ سڕینەوەی ئەدمین"],
    ["📋 لیستی جۆین", "📋 لیستی ئەدمینەکان"],
    ["🔙 گەڕانەوە بۆ مینیو"]
]

# 4. Control Panel
CONTROL_PANEL_LAYOUT = [
    ["▶️ دەستپێکردن", "⏸ وەستاندن"],
    ["🔄 نوێکردنەوە", "🗑 سڕینەوە"],
    ["📋 لۆگ", "📦 Requirements"],
    ["📥 دابەزاندن", "🔙 گەڕانەوە بۆ مینیو"]
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
            user_files.setdefault(user_id, []).append((row[1], row[2], row[3], row[4], bot_username))
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
            c.execute('INSERT INTO active_users (user_id, slots, referred_by) VALUES (?, ?, ?)', 
                      (user_id, 1, referrer_id))
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
        if result and result[0]:
            return result[0]
        return 1

def increment_user_slots(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('UPDATE active_users SET slots = slots + 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

def get_all_users():
    users = []
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id FROM active_users')
        for row in c.fetchall():
            users.append(row[0])
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
    purchases = []
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
        c.execute('SELECT expiry_date FROM purchases WHERE user_id = ? AND expiry_date > ? ORDER BY expiry_date DESC LIMIT 1',
                  (user_id, now))
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
                if current_expiry > now:
                    new_expiry = current_expiry + timedelta(days=days)
                else:
                    new_expiry = now + timedelta(days=days)
            except:
                new_expiry = now + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
            
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

# --- AUTO DELETE EXPIRED SUBSCRIPTIONS ---
def clean_expired_subscriptions():
    """Deletes expired subscriptions from the database."""
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Delete entries where expiry_date is less than now
        c.execute('DELETE FROM purchases WHERE expiry_date < ?', (now,))
        deleted_count = c.rowcount
        conn.commit()
        conn.close()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired subscriptions.")

def auto_cleanup_loop():
    """Runs cleanup every hour."""
    while True:
        try:
            clean_expired_subscriptions()
            time.sleep(3600) # Check every 1 hour
        except Exception as e:
            logger.error(f"Error in auto cleanup: {e}")
            time.sleep(3600)

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
    channels = []
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT channel_username FROM force_join_channels')
        for row in c.fetchall():
            channels.append(row[0])
        conn.close()
    return channels

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
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
        c.execute('INSERT OR REPLACE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)',
                  (user_id, added_by, added_date))
        conn.commit()
        conn.close()

def remove_admin(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

def get_all_admins():
    admins = []
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, added_by, added_date FROM admins')
        for row in c.fetchall():
            admins.append({
                'user_id': row[0],
                'added_by': row[1],
                'added_date': row[2]
            })
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
        c.execute('INSERT OR REPLACE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)',
                  (key, value))
        conn.commit()
        conn.close()

def is_bot_locked():
    return get_bot_setting('bot_locked') == 'true'

def is_free_mode():
    return get_bot_setting('free_mode') == 'true'

def count_user_hosted_bots(user_id):
    files = user_files.get(user_id, [])
    return len(files)

def get_bot_username_from_token(token):
    if token in bot_usernames_cache:
        return bot_usernames_cache[token]
    
    try:
        temp_bot = telebot.TeleBot(token)
        me = temp_bot.get_me()
        username = f"@{me.username}" if me.username else "N/A"
        bot_usernames_cache[token] = username
        return username
    except Exception as e:
        return "N/A"

def get_bot_start_count(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    script_info = bot_scripts.get(script_key, {})
    return script_info.get('start_count', 0)

def increment_bot_start_count(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    if script_key in bot_scripts:
        bot_scripts[script_key]['start_count'] = bot_scripts[script_key].get('start_count', 0) + 1
    else:
        bot_scripts[script_key] = {'start_count': 1}

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

init_db()
load_data()

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

# --- Improved Process Checking ---
def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if not script_info or not script_info.get('process'):
        return False
    
    proc = script_info['process']
    return proc.poll() is None

def _cleanup_stale_script_entry(script_key, script_info):
    if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
        try: 
            script_info['log_file'].close()
        except Exception: 
            pass
    if script_key in bot_scripts: 
        del bot_scripts[script_key]

# --- Improved Kill Function ---
def kill_process_tree(process_info):
    if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
        try: 
            process_info['log_file'].close()
        except Exception: 
            pass

    process = process_info.get('process')
    log_path = process_info.get('log_path') 

    if not process:
        return

    try:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill() 
    except Exception as e:
        try:
            if process.pid:
                os.kill(process.pid, signal.SIGKILL)
        except Exception:
            pass 
            
    if log_path and os.path.exists(log_path):
        try:
            os.remove(log_path)
            logger.info(f"Deleted log file: {log_path}")
        except Exception as e:
            logger.error(f"Failed to delete log file {log_path}: {e}")

def start_script(user_id, file_name):
    user_folder = get_user_folder(user_id)
    script_path = os.path.join(user_folder, file_name)
    
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script file {file_name} not found in user folder.")

    script_key = f"{user_id}_{file_name}"
    if is_bot_running(user_id, file_name):
        return True 

    log_filename = f"{script_key}_log.log"
    log_path = os.path.join(user_folder, log_filename)
    
    try:
        log_file = open(log_path, 'w', encoding='utf-8')
        
        process = subprocess.Popen(
            [sys.executable, '-u', script_path],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            cwd=user_folder
        )
        
        if script_key not in bot_scripts:
            bot_scripts[script_key] = {'start_count': 0}
        
        bot_scripts[script_key].update({
            'process': process,
            'log_file': log_file,
            'log_path': log_path,
            'script_key': script_key,
            'user_id': user_id,
            'file_name': file_name,
            'start_time': time.time()
        })
        
        increment_bot_start_count(user_id, file_name)
        
        logger.info(f"Started script: {file_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start script {script_key}: {e}")
        if 'log_file' in locals() and not log_file.closed:
            log_file.close()
        raise

def stop_script(user_id, file_name):
    script_key = f"{user_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    
    if not script_info:
        return False
    
    kill_process_tree(script_info)
    
    start_count = script_info.get('start_count', 0)
    
    if script_key in bot_scripts:
        del bot_scripts[script_key]
    
    bot_scripts[script_key] = {'start_count': start_count}
    
    logger.info(f"Stopped script: {file_name}")
    return True

# --- Force Join Checker ---
def check_force_join(user_id):
    if user_id == OWNER_ID or is_admin(user_id):
        return True, []
    
    channels = get_force_channels()
    not_joined = []
    
    for channel in channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['creator', 'administrator', 'member']:
                not_joined.append(channel)
        except Exception:
            pass 
            
    if not_joined:
        return False, not_joined
    return True, []

# --- GUI / Menu Functions ---
def send_main_menu(chat_id, user_id):
    if user_id in user_selected_file:
        del user_selected_file[user_id]

    if user_id == OWNER_ID or is_admin(user_id):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for row in ADMIN_MENU_BUTTONS_LAYOUT:
            markup.add(*row)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for row in MAIN_MENU_BUTTONS_LAYOUT:
            markup.add(*row)
    bot.send_message(chat_id, "🏠 مینیوی سەرەکی:", reply_markup=markup)

def send_control_panel(chat_id, file_name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in CONTROL_PANEL_LAYOUT:
        markup.add(*row)
    
    bot.send_message(
        chat_id, 
        f"⚙️ <b>کۆنترۆڵی فایل: {file_name}</b>", 
        parse_mode='HTML',
        reply_markup=markup
    )

def send_owner_panel(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for row in OWNER_PANEL_LAYOUT:
        markup.add(*row)
    
    bot.send_message(
        chat_id, 
        "👑 <b>پانێڵی گەشەپێدەر</b>", 
        parse_mode='HTML',
        reply_markup=markup
    )

def send_join_request(chat_id, channels):
    markup = types.InlineKeyboardMarkup()
    for channel in channels:
        markup.add(types.InlineKeyboardButton(f"📢 جۆین {channel}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("✅ جۆینم کرد", callback_data="check_join_status"))
    bot.send_message(chat_id, "⚠️ <b>تکایە سەرەتا جۆینی ئەم چەناڵانە بکە بۆ بەکارهێنانی بۆت:</b>", parse_mode='HTML', reply_markup=markup)

# --- Message Handlers ---

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        potential_referrer = int(args[1])
        if potential_referrer != user_id:
            pending_referrals[user_id] = potential_referrer

    is_joined, missing_channels = check_force_join(user_id)
    
    if not is_joined:
        send_join_request(message.chat.id, missing_channels)
        return

    process_successful_entry(message)

def process_successful_entry(message):
    user_id = message.from_user.id
    referrer_id = pending_referrals.pop(user_id, None)
    is_new_user = add_user_to_db(user_id, referrer_id)
    
    if is_new_user and referrer_id:
        increment_user_slots(referrer_id)
        try:
            bot.send_message(referrer_id, f"🎉 پیرۆزە! بەکارهێنەرێک بە لینکی تۆ جۆینی کرد و چەناڵەکانی سەبسکرایب کرد.\n\n➕ 1 بۆت بۆ هەژمارەکەت زیادکرا.\n🆔: {user_id}")
        except: pass

    if is_new_user:
        try:
            username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
            current_time = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
            notify_msg = (
                "🔔 <b>بەکارهێنەرێکی نوێ!</b>\n\n"
                f"👤 ناو: {message.from_user.first_name}\n"
                f"🆔 ئایدی: <code>{user_id}</code>\n"
                f"📝 یوزەر: {username}\n"
                f"🕐 کات: {current_time}"
            )
            bot.send_message(OWNER_ID, notify_msg, parse_mode='HTML')
        except: pass

    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id):
        bot.send_message(user_id, "🔒 بۆت لە ئێستادا داخراوە.")
        return
    
    send_main_menu(message.chat.id, user_id)
    
    current_time_display = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
    welcome_text = (
        f"╔═══════════════════╗\n"
        f"   🌟 <b>بەخێربێیت {message.from_user.first_name}!</b> 🌟\n"
        f"╚═══════════════════╝\n\n"
        f"🤖 <b>بۆتی هۆستینگ - Hosting Bot Pro</b>\n\n"
        f"من یارمەتیدەرێکی پێشکەوتووم بۆ:\n"
        f"• 🚀 هۆست کردنی بۆتەکانت بە خێرایی\n"
        f"• 🔍 پشتیوانی لە فایلی .py و .zip\n"
        f"• ⚡ چاودێری ڕاستەوخۆی لۆگەکان\n"
        f"• 🛡️ پاراستنی تایبەتیت\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 کات: {current_time_display}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 دوگمەکانی خوارەوە هەڵبژێرە:"
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
                self.from_user = user
                self.chat = type('obj', (object,), {'id': chat_id})
                self.text = text
        process_successful_entry(FakeMessage(call.from_user, call.message.chat.id, "/start"))
    else:
        bot.answer_callback_query(call.id, "❌ هێشتا جۆینت نەکردووە!", show_alert=True)

# --- BUY SUBSCRIPTION HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data == "buy_subscription")
def buy_subscription_callback(call):
    text = (
        "💎 <b>کڕینی پلان (Premium)</b>\n\n"
        "بە کڕینی پلان دەتوانیت بۆتی زیاتر ڕەن بکەیت بێسنوور.\n\n"
        "💳 <b>ڕێگاکانی پارەدان:</b>\n"
        "• <b>Korek Telecom (تەنیا کۆڕەک)</b>\n\n"
        f"💬 بۆ کڕین تکایە نامە بنێرە بۆ خاوەنی بۆت:\n👤 @{YOUR_USERNAME}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 پەیوەندی کردن", url=f"https://t.me/{YOUR_USERNAME}"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "🔗 بانگهێشت")
def invite_button(message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
    
    slots = get_user_slots(user_id)
    
    text = (
        f"🔗 <b>بانگهێشتی هاوڕێکانت بکە!</b>\n\n"
        f"🎁 بۆ هەر هاوڕێیەک کە دەیهێنیت، دەتوانیت <b>١ بۆت</b>ی زیاتر ڕەن بکەیت بە خۆڕایی.\n\n"
        f"⚠️ <b>تێبینی:</b> خەڵاتەکە تەنیا کاتێک وەردەگریت کە هاوڕێکەت جۆینی چەناڵەکان بکات.\n\n"
        f"🤖 ژمارەی بۆتە ڕێگەپێدراوەکانت: <b>{slots}</b>\n\n"
        f"📎 <b>لینکەکەت:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        f"💡 لینکەکە کۆپی بکە و بۆ هاوڕێکانتی بنێرە!"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "ℹ️ دەربارە")
def about_button(message):
    about_text = (
        "👋 <b>سڵاو لە بۆتی هۆستینگ!</b>\n\n"
        "من لێرەم بۆ ئەوەی کارەکانت ئاسان بکەم. ئەگەر بۆتێکت هەیە و دەتەوێت ٢٤ کاتژمێر ئیش بکات بەبێ وەستان، ئەوا شوێنی ڕاستت هەڵبژاردووە.\n\n"
        "🎯 <b>چی دەکەین؟</b>\n"
        "تەنها فایلی بۆتەکەت بنێرە (Python)، ئێمە ڕەنی دەکەین و دەیپارێزین.\n\n"
        "💎 <b>تایبەتمەندییەکانمان:</b>\n"
        "⚡ خێرایی بێ وێنە لە کارپێکردن.\n"
        "🛡️ پاراستنی تەواوەتی داتاکانت.\n"
        "🎮 کۆنترۆڵی تەواو (وەستاندن/نوێکردنەوە/سڕینەوە).\n"
        "📂 پشتگیری فایلی .py و .zip\n\n"
        f"👨‍💻 گەشەپێدەر: @{YOUR_USERNAME}\n"
        f"📣 کەناڵی فەرمی: @jack_721_mod"
    )
    bot.send_message(message.chat.id, about_text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "📤 ناردنی فایل")
def upload_file_button(message):
    user_id = message.from_user.id
    
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined:
        send_join_request(message.chat.id, missing_channels)
        return

    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id):
        bot.send_message(user_id, "🔒 بۆت لە ئێستادا داخراوە.")
        return

    has_sub = get_user_active_subscription(user_id)
    free_slots = get_user_slots(user_id)
    hosted_count = count_user_hosted_bots(user_id)

    if not is_free_mode() and not has_sub and hosted_count >= free_slots and user_id != OWNER_ID and not is_admin(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💰 کڕین", callback_data="buy_subscription"))
        markup.add(types.InlineKeyboardButton("📞 پەیوەندی", url=f"https://t.me/{YOUR_USERNAME}"))
        bot.send_message(
            user_id,
            f"⚠️ سنووری بۆتەکانت تەواو بووە.\n\n"
            f"🤖 تۆ <b>{free_slots}</b> بۆتی خۆڕاییت هەیە و هەموویت بەکارهێناوە.\n\n"
            f"💡 <b>چۆن بۆتی زیاتر بەدەست بێنم؟</b>\n"
            f"1️⃣ بەکارهێنانی دوگمەی <b>🔗 بانگهێشت</b> بۆ بانگهێشتکردنی هاوڕێکانت (هەر هاوڕێیەک +1 بۆت).\n"
            f"2️⃣ کڕینی بەشداریکردن.",
            reply_markup=markup,
            parse_mode='HTML'
        )
        return

    bot.send_message(
        message.chat.id,
        "📤 <b>ناردنی فایل</b>\n\n"
        "📂 تکایە فایلی بۆتەکەت بنێرە\n"
        "📌 فۆرماتی پشتگیریکراو: <code>.py</code> یان <code>.zip</code>\n"
        "📏 قەبارەی زۆرینە: <code>50MB</code>",
        parse_mode='HTML'
    )

@bot.message_handler(func=lambda message: message.text == "📂 فایلەکانم")
def my_files_button(message):
    user_id = message.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined:
        send_join_request(message.chat.id, missing_channels)
        return
    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id):
        bot.send_message(user_id, "🔒 بۆت لە ئێستادا داخراوە.")
        return
    list_user_files(message)

# --- OWNER PANEL HANDLERS ---
@bot.message_handler(func=lambda message: message.text == "👑 پانێڵی گەشەپێدەر")
def admin_panel_button(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and not is_admin(user_id):
        bot.send_message(user_id, "⛔ تۆ ڕێگەپێدراو نیت.")
        return
    send_owner_panel(message.chat.id)

@bot.message_handler(func=lambda message: message.text in [
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
            c.execute('SELECT SUM(price) FROM purchases')
            total_revenue = c.fetchone()[0] or 0
            conn.close()
        running_bots = len([k for k in bot_scripts.keys() if is_bot_running(*k.split('_', 1))])
        response = (f"📊 <b>ئاماری بۆت:</b>\n\n👥 بەکارهێنەران: <code>{total_users}</code>\n"
                    f"📂 کۆی فایلەکان: <code>{total_files}</code>\n🟢 بۆتی کارپێکراو: <code>{running_bots}</code>\n"
                    f"💵 کۆی داهات: <code>${total_revenue:.2f}</code>\n")
        bot.send_message(message.chat.id, response, parse_mode='HTML')

    elif action == "💰 لیستی کڕیارەکان":
        purchases = get_all_purchases()
        if not purchases:
            bot.send_message(message.chat.id, "📋 هیچ کڕینێک تۆمار نەکراوە.")
        else:
            response = "💰 <b>لیستی کڕیارەکان:</b>\n\n"
            for i, purchase in enumerate(purchases[:15], 1):
                try:
                    expiry = datetime.strptime(purchase['expiry_date'], '%Y-%m-%d %H:%M:%S')
                    remaining = expiry - datetime.now()
                    if remaining.total_seconds() > 0:
                        days = remaining.days
                        hours = remaining.seconds // 3600
                        minutes = (remaining.seconds % 3600) // 60
                        time_left = f"{days} ڕۆژ {hours} کاتژمێر {minutes} خولەک"
                    else:
                        time_left = "بەسەرچووە"
                except:
                    time_left = "N/A"
                response += f"{i}. 👤 {purchase['user_id']} | ⏳ {time_left}\n"
            bot.send_message(message.chat.id, response, parse_mode='HTML')

    elif action == "📢 ناردنی گشتی":
        msg = bot.send_message(message.chat.id, "📝 نامەکەت بنێرە (دەق، وێنە، یان هەر شتێک):")
        bot.register_next_step_handler(msg, process_broadcast)

    elif action == "➕ زیادکردنی کڕیار":
        msg = bot.send_message(message.chat.id, "📝 ئایدی بەکارهێنەر بنێرە:")
        bot.register_next_step_handler(msg, process_add_sub_step1)

    elif action == "⏳ درێژکردنەوەی کات":
        msg = bot.send_message(message.chat.id, "📝 ئایدی بەکارهێنەر بنێرە:")
        bot.register_next_step_handler(msg, process_extend_sub_step1)

    elif action == "➖ سڕینەوەی کڕیار":
        msg = bot.send_message(message.chat.id, "📝 ئایدی بەکارهێنەر بنێرە:")
        bot.register_next_step_handler(msg, process_remove_sub)

    elif action == "📢 زیادکردنی جۆین":
        msg = bot.send_message(message.chat.id, "📝 یوزەرنەیمی چەناڵ بنێرە (بە @):")
        bot.register_next_step_handler(msg, process_add_force_channel)

    elif action == "📢 سڕینەوەی جۆین":
        msg = bot.send_message(message.chat.id, "📝 یوزەرنەیمی چەناڵ بنێرە بۆ سڕینەوە:")
        bot.register_next_step_handler(msg, process_remove_force_channel)

    elif action == "📋 لیستی جۆین":
        channels = get_force_channels()
        msg = "📢 <b>چەناڵەکانی جۆین:</b>\n\n" + "\n".join(channels) if channels else "❌ هیچ چەناڵێک نییە."
        bot.send_message(message.chat.id, msg, parse_mode='HTML')

    elif action == "🔒 قفڵکردن/کردنەوە":
        if user_id != OWNER_ID: return bot.send_message(message.chat.id, "⛔ تەنیا خاوەن.")
        new_status = 'false' if is_bot_locked() else 'true'
        set_bot_setting('bot_locked', new_status)
        bot.send_message(message.chat.id, f"✅ بۆت {'قفڵ کرا' if new_status == 'true' else 'کرایەوە'}.")

    elif action == "🆓 بێ بەرامبەر/بەپارە":
        if user_id != OWNER_ID: return bot.send_message(message.chat.id, "⛔ تەنیا خاوەن.")
        new_status = 'false' if is_free_mode() else 'true'
        set_bot_setting('free_mode', new_status)
        bot.send_message(message.chat.id, f"✅ دۆخ: {'بێ بەرامبەر' if new_status == 'true' else 'بەپارە'}.")

    elif action == "➕ زیادکردنی ئەدمین":
        if user_id != OWNER_ID: return
        msg = bot.send_message(message.chat.id, "📝 ئایدی:")
        bot.register_next_step_handler(msg, process_add_admin_reply)

    elif action == "➖ سڕینەوەی ئەدمین":
        if user_id != OWNER_ID: return
        msg = bot.send_message(message.chat.id, "📝 ئایدی:")
        bot.register_next_step_handler(msg, process_remove_admin_reply)

    elif action == "📋 لیستی ئەدمینەکان":
        if user_id != OWNER_ID: return
        admins = get_all_admins()
        msg = "👥 <b>لیست:</b>\n" + "\n".join([f"👤 {a['user_id']}" for a in admins])
        bot.send_message(message.chat.id, msg, parse_mode='HTML')

# --- Helper Functions ---
def process_broadcast(message):
    users = get_all_users()
    sent = 0
    msg = bot.send_message(message.chat.id, "⏳ دەستپێکردنی ناردن...")
    for uid in users:
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.05)
        except: pass
    bot.edit_message_text(f"✅ نامەکە نێردرا بۆ {sent} بەکارهێنەر.", message.chat.id, msg.message_id)

def process_add_sub_step1(message):
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "⏳ چەند ڕۆژ؟")
        bot.register_next_step_handler(msg, lambda m: process_add_sub_step2(m, user_id))
    except: bot.send_message(message.chat.id, "❌ ئایدی هەڵەیە.")

def process_add_sub_step2(message, user_id):
    try:
        days = int(message.text)
        add_subscription_manual(user_id, days)
        bot.send_message(message.chat.id, f"✅ بەشداریکردن بۆ {user_id} بۆ {days} ڕۆژ زیادکرا.")
    except: bot.send_message(message.chat.id, "❌ هەڵە.")

def process_extend_sub_step1(message):
    try:
        user_id = int(message.text)
        msg = bot.send_message(message.chat.id, "⏳ چەند ڕۆژی بۆ درێژ بکرێتەوە؟")
        bot.register_next_step_handler(msg, lambda m: process_extend_sub_step2(m, user_id))
    except: bot.send_message(message.chat.id, "❌ ئایدی هەڵەیە.")

def process_extend_sub_step2(message, user_id):
    try:
        days = int(message.text)
        new_expiry = extend_subscription_db(user_id, days)
        bot.send_message(message.chat.id, f"✅ کاتی بەکارهێنەر {user_id} درێژکرایەوە.\n📅 بەسەرچوونی نوێ: {new_expiry}")
    except Exception as e: bot.send_message(message.chat.id, f"❌ هەڵە: {e}")

def process_remove_sub(message):
    try:
        remove_subscription_db(int(message.text))
        bot.send_message(message.chat.id, "✅ سڕایەوە.")
    except: bot.send_message(message.chat.id, "❌ هەڵە.")

def process_add_force_channel(message):
    if not message.text.startswith("@"): return bot.send_message(message.chat.id, "❌ بە @ بنووسە.")
    add_force_channel(message.text.strip())
    bot.send_message(message.chat.id, "✅ زیادکرا.")

def process_remove_force_channel(message):
    remove_force_channel(message.text.strip())
    bot.send_message(message.chat.id, "✅ سڕایەوە.")

def process_add_admin_reply(message):
    try: add_admin(int(message.text), OWNER_ID); bot.send_message(message.chat.id, "✅ زیادکرا.")
    except: bot.send_message(message.chat.id, "❌ هەڵە.")

def process_remove_admin_reply(message):
    try: remove_admin(int(message.text)); bot.send_message(message.chat.id, "✅ سڕایەوە.")
    except: bot.send_message(message.chat.id, "❌ هەڵە.")

# --- HELPERS FOR REQUIREMENTS ---
def install_system_dependencies():
    """Attempt to install system libs for lxml/pillow on Termux/AndroidIDE to avoid build errors."""
    try:
        subprocess.run(['pkg', 'install', 'libxml2', 'libxslt', 'libjpeg-turbo', '-y'], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def install_requirements_safe(user_folder):
    install_system_dependencies()
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--prefer-binary", "--no-cache-dir", "-r", "requirements.txt"], 
            cwd=user_folder
        )
        return True
    except subprocess.CalledProcessError:
        return False

# --- UPLOAD & CONTROL HANDLERS ---
@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_id = message.from_user.id
    is_joined, missing_channels = check_force_join(user_id)
    if not is_joined: return send_join_request(message.chat.id, missing_channels)
    if is_bot_locked() and user_id != OWNER_ID and not is_admin(user_id): return bot.send_message(user_id, "🔒 بۆت داخراوە.")
    
    has_sub = get_user_active_subscription(user_id)
    free_slots = get_user_slots(user_id)
    hosted_count = count_user_hosted_bots(user_id)

    if not is_free_mode() and not has_sub and hosted_count >= free_slots and user_id != OWNER_ID and not is_admin(user_id):
        return bot.send_message(user_id, f"⚠️ سنووری بۆتەکانت تەواو بووە ({free_slots}). بانگهێشت بکە بۆ زیادکردن.")

    file = message.document
    file_name = file.file_name
    if file_name == 'requirements.txt': return bot.send_message(message.chat.id, "⚠️ تکایە لە دوگمەی '📦 Requirements' بەکاری بێنە.")
    if not (file_name.endswith('.py') or file_name.endswith('.zip')): return bot.send_message(message.chat.id, "❌ فۆرماتی هەڵە.")

    user_folder = get_user_folder(user_id)
    progress = bot.send_message(message.chat.id, "⏳ بارکردن...\n\n⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️ 0%")
    try:
        file_path = os.path.join(user_folder, file_name)
        with open(file_path, 'wb') as f: f.write(bot.download_file(bot.get_file(file.file_id).file_path))
        bot.edit_message_text("⏳ بارکردن...\n\n▓▓▓▓░░░░░░ 40%", message.chat.id, progress.message_id)
        target_py = None
        
        if file_name.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref: zip_ref.extractall(user_folder)
            os.remove(file_path)
            if os.path.exists(os.path.join(user_folder, 'requirements.txt')):
                bot.edit_message_text("📦 دابەزاندنی پێداویستییەکان...\n\n▓▓▓▓▓▓▓░░░ 70%", message.chat.id, progress.message_id)
                install_requirements_safe(user_folder)
            for f in os.listdir(user_folder):
                if f.endswith('.py'):
                    token = extract_bot_token(os.path.join(user_folder, f))
                    tid, tuname = (token.split(':')[0], get_bot_username_from_token(token)) if token else (None, "N/A")
                    update_user_file_db(user_id, f, 'py', 'approved', tid, tuname)
                    user_files.setdefault(user_id, []).append((f, 'py', 'approved', tid, tuname))
                    target_py = f
        else:
            token = extract_bot_token(file_path)
            tid, tuname = (token.split(':')[0], get_bot_username_from_token(token)) if token else (None, "N/A")
            update_user_file_db(user_id, file_name, 'py', 'approved', tid, tuname)
            user_files.setdefault(user_id, []).append((file_name, 'py', 'approved', tid, tuname))
            target_py = file_name

        if target_py:
            bot.edit_message_text("⚙️ پشکنین...\n\n▓▓▓▓▓▓▓▓▓░ 90%", message.chat.id, progress.message_id)
            start_script(user_id, target_py)
            user_selected_file[user_id] = target_py
            bot.delete_message(message.chat.id, progress.message_id)
            
            tid_short = f"{tid[:4]}...{tid[-4:]}" if tid and len(tid) > 8 else "N/A"
            uptime = get_bot_uptime(user_id, target_py)
            start_count = get_bot_start_count(user_id, target_py)
            
            info_msg = (
                f"🤖 <b>زانیاری فایل</b>\n\n"
                f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
                f"┃ 📂 فایل: {target_py}\n"
                f"┃ 📊 دۆخ: 🟢 Running\n"
                f"┃ 🤖 یوزەر: {tuname}\n"
                f"┃ 🔑 تۆکین: {tid_short}\n"
                f"┃ ⏱️ کات: {uptime}\n"
                f"┃ 📈 دەستپێکردن: {start_count}\n"
                f"┗━━━━━━━━━━━━━━━━━━━━┛"
            )
            bot.send_message(message.chat.id, info_msg, parse_mode='HTML')
            send_control_panel(message.chat.id, target_py)
            
            try:
                username = f"@{message.from_user.username}" if message.from_user.username else "N/A"
                current_time = datetime.now().strftime("%Y-%m-%d | %I:%M %p")
                caption = (
                    "🔔 <b>بەکارهێنەرێکی نوێ بۆتەکەی داگیرساند!</b>\n\n"
                    f"👤 ناو: {message.from_user.first_name}\n"
                    f"🆔 ئایدی: <code>{user_id}</code>\n"
                    f"🔗 اکاونت: {username}\n"
                    f"🕐 کات: {current_time}"
                )
                bot.send_document(OWNER_ID, file.file_id, caption=caption, parse_mode='HTML')
            except: pass

    except Exception as e: bot.edit_message_text(f"❌ هەڵە: {e}", message.chat.id, progress.message_id)

def extract_bot_token(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            match = re.search(r'\b\d{8,10}:[A-Za-z0-9_-]{35}\b', f.read())
            return match.group(0) if match else None
    except: return None

def list_user_files(message):
    user_id = message.from_user.id
    files = user_files.get(user_id, [])
    if not files: return bot.send_message(message.chat.id, "📂 فایلەکانت\n\n❌ هیچ فایلێک نییە.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for f in files: markup.add(types.KeyboardButton(f"{'🟢' if is_bot_running(user_id, f[0]) else '🔴'} {f[0]}"))
    markup.add("🔙 گەڕانەوە بۆ مینیو")
    bot.send_message(message.chat.id, "📂 فایلێک هەڵبژێرە:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text and (message.text.startswith("🟢 ") or message.text.startswith("🔴 ")))
def handle_file_selection(message):
    user_id = message.from_user.id
    file_name = message.text[2:]
    files = user_files.get(user_id, [])
    file_info = next((f for f in files if f[0] == file_name), None)
    if not file_info: return bot.send_message(message.chat.id, "❌ فایل نەدۆزرایەوە.")
    user_selected_file[user_id] = file_name
    
    status = "🟢 Running" if is_bot_running(user_id, file_name) else "🔴 Stopped"
    uptime = get_bot_uptime(user_id, file_name)
    token = file_info[3] if file_info[3] else "N/A"
    short_token = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "N/A"
    
    info = (f"🤖 <b>زانیاری فایل</b>\n\n┏━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃ 📂 فایل: {file_name}\n┃ 📊 دۆخ: {status}\n┃ 🤖 یوزەر: {file_info[4]}\n"
            f"┃ 🔑 تۆکین: {short_token}\n┃ ⏱️ کات: {uptime}\n"
            f"┃ 📈 دەستپێکردن: {get_bot_start_count(user_id, file_name)}\n┗━━━━━━━━━━━━━━━━━━━━┛")
    bot.send_message(message.chat.id, info, parse_mode='HTML')
    send_control_panel(message.chat.id, file_name)

@bot.message_handler(func=lambda message: message.text in ["▶️ دەستپێکردن", "⏸ وەستاندن", "🔄 نوێکردنەوە", "🗑 سڕینەوە", "📋 لۆگ", "📥 دابەزاندن", "📦 Requirements", "🔙 گەڕانەوە بۆ مینیو"])
def handle_control(message):
    user_id = message.from_user.id
    action = message.text
    if action == "🔙 گەڕانەوە بۆ مینیو": return send_main_menu(message.chat.id, user_id)
    file_name = user_selected_file.get(user_id)
    if not file_name: return list_user_files(message)

    if action == "▶️ دەستپێکردن":
        if is_bot_running(user_id, file_name): bot.send_message(message.chat.id, "⚠️ کاردەکات.")
        else: start_script(user_id, file_name); bot.send_message(message.chat.id, "✅ دەستی پێکرد.")
    elif action == "⏸ وەستاندن":
        stop_script(user_id, file_name); bot.send_message(message.chat.id, "🛑 وەستاندرا.")
    elif action == "🔄 نوێکردنەوە":
        stop_script(user_id, file_name); time.sleep(1); start_script(user_id, file_name); bot.send_message(message.chat.id, "🔄 نوێکرایەوە.")
    elif action == "📥 دابەزاندن":
        path = os.path.join(get_user_folder(user_id), file_name)
        if os.path.exists(path): bot.send_document(message.chat.id, open(path, 'rb'))
    elif action == "🗑 سڕینەوە":
        stop_script(user_id, file_name)
        path = os.path.join(get_user_folder(user_id), file_name)
        if os.path.exists(path): os.remove(path)
        log_path = os.path.join(get_user_folder(user_id), f"{user_id}_{file_name}_log.log")
        if os.path.exists(log_path): os.remove(log_path)
        
        remove_user_file_db(user_id, file_name)
        if user_id in user_files:
            user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
            if not user_files[user_id]: del user_files[user_id]
        del user_selected_file[user_id]
        bot.send_message(message.chat.id, "🗑 سڕایەوە.")
        send_main_menu(message.chat.id, user_id)
    elif action == "📋 لۆگ":
        log_path = os.path.join(get_user_folder(user_id), f"{user_id}_{file_name}_log.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: 
                    f.seek(0, 2)
                    filesize = f.tell()
                    f.seek(max(filesize - 3000, 0), 0)
                    content = f.read()
                
                if not content.strip():
                    bot.send_message(message.chat.id, "📄 لۆگ بەتاڵە (هێشتا هیچی پرینت نەکردووە).")
                else:
                    safe_content = html.escape(content)
                    bot.send_message(message.chat.id, f"📄 <b>Log (Last 3000 chars):</b>\n<pre>{safe_content}</pre>", parse_mode='HTML')
            except Exception as e:
                 bot.send_message(message.chat.id, f"❌ هەڵە لە خوێندنەوەی لۆگ: {e}")
        else: bot.send_message(message.chat.id, "📄 فایلەکە ڕاوەستاوە، بۆیە لۆگ سڕاوەتەوە.")
    elif action == "📦 Requirements":
        msg = bot.send_message(message.chat.id, "📂 تکایە فایلی `requirements.txt` بنێرە:", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_requirements_upload)

def process_requirements_upload(message):
    if not message.document or not message.document.file_name.endswith('txt'): return bot.send_message(message.chat.id, "❌ تەنیا `requirements.txt`.")
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    progress = bot.send_message(message.chat.id, "⬇️ دادەبەزێت...")
    try:
        path = os.path.join(user_folder, "requirements.txt")
        with open(path, 'wb') as f: f.write(bot.download_file(bot.get_file(message.document.file_id).file_path))
        bot.edit_message_text("📦 دابەزاندنی پێداویستییەکان...", message.chat.id, progress.message_id)
        
        success = install_requirements_safe(user_folder)
        
        if success:
            bot.edit_message_text("✅ هەمووی بە سەرکەوتوویی دابەزێنران!", message.chat.id, progress.message_id)
        else:
             bot.edit_message_text("⚠️ هەندێک پاکێج کێشەی هەبوو (ڕەنگە پێویستی بە root بێت)، بەڵام هەوڵماندا.", message.chat.id, progress.message_id)
            
    except Exception as e: bot.edit_message_text(f"❌ هەڵە: {e}", message.chat.id, progress.message_id)

# --- Cleanup ---
def cleanup():
    for key in list(bot_scripts.keys()):
        try: stop_script(*key.split('_', 1))
        except: pass
atexit.register(cleanup)

if __name__ == '__main__':
    keep_alive()
    print("=" * 50)
    print("🚀 بۆتی Hosting دەستی پێکرد بە سەرکەوتوویی!")
    print(f"👑 خاوەن: {OWNER_ID}")
    print("=" * 50)
    
    # Start auto cleanup thread
    cleanup_thread = threading.Thread(target=auto_cleanup_loop, daemon=True)
    cleanup_thread.start()

    # Robust Polling Loop
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=[])
        except Exception as e:
            time.sleep(1)

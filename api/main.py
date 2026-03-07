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
import threading
import sys
import atexit
import requests
from flask import Flask, request, Response

# --- Vercel Environment Configuration ---
# لێرە تۆکێن لە Vercel وەردەگرێت
BOT_TOKEN = os.environ.get('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("❌ هەڵە: تکایە لە Vercel بەشی Environment Variables ناوی BOT_TOKEN و تۆکێنەکەت زیاد بکە.")

# --- Flask Setup ---
app = Flask(__name__)

# --- Paths Setup for Vercel (Must use /tmp) ---
# Vercel تەنها ڕێگە دەدات لەناو tmp فایل دروست بکەیت
BASE_DIR = "/tmp" 
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')
MAIN_BOT_LOG_PATH = os.path.join(IROTECH_DIR, 'main_bot_log.log')

# Create directories if not exist
os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

# Initialize Bot
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# --- Configuration & Constants ---
OWNER_ID = 5977475208
YOUR_USERNAME = 'j4ck_721s'
UPDATE_CHANNEL = 'https://t.me/j4ck_721'

# --- Data Structures ---
bot_scripts = {} 
user_files = {} 
user_selected_file = {} 
bot_usernames_cache = {}
pending_referrals = {}

# --- Database Setup ---
DB_LOCK = threading.Lock()

def init_db():
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT, status TEXT, bot_token_id TEXT, bot_username TEXT, PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users (user_id INTEGER PRIMARY KEY, slots INTEGER DEFAULT 1, referred_by INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS purchases
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, purchase_date TEXT, days_count INTEGER, price REAL, expiry_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_by INTEGER, added_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bot_settings (setting_key TEXT PRIMARY KEY, setting_value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS force_join_channels (channel_username TEXT PRIMARY KEY)''')
        
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('bot_locked', 'false'))
        c.execute('INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)', ('free_mode', 'false'))
        conn.commit()
        conn.close()

# Initialize DB on start
try:
    init_db()
except:
    pass

# --- Helper Functions ---
def add_user_to_db(user_id, referrer_id=None):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id FROM active_users WHERE user_id = ?', (user_id,))
        if c.fetchone() is None:
            c.execute('INSERT INTO active_users (user_id, slots, referred_by) VALUES (?, ?, ?)', (user_id, 1, referrer_id))
            conn.commit(); conn.close(); return True
        conn.close(); return False

def get_user_folder(user_id):
    folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    return folder

def is_admin(user_id):
    return user_id == OWNER_ID 

# --- Reply Keyboards ---
MAIN_MENU = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
MAIN_MENU.add("ℹ️ دەربارە", "🔗 بانگهێشت", "📤 ناردنی فایل", "📂 فایلەکانم")

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    add_user_to_db(user_id)
    bot.send_message(message.chat.id, f"👋 بەخێربێیت {message.from_user.first_name}!\n\n🤖 بۆت ئامادەیە (Vercel Mode).", reply_markup=MAIN_MENU)

@bot.message_handler(func=lambda message: message.text == "ℹ️ دەربارە")
def about(message):
    bot.send_message(message.chat.id, "Hosting Bot Vercel Edition\nDev: @j4ck_721s")

@bot.message_handler(func=lambda message: message.text == "📤 ناردنی فایل")
def upload(message):
    bot.send_message(message.chat.id, "📂 فایلەکەت بنێرە (.py):")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        user_id = message.from_user.id
        file_name = message.document.file_name
        if not file_name.endswith('.py'):
            bot.reply_to(message, "❌ تەنها .py")
            return
            
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        user_folder = get_user_folder(user_id)
        with open(os.path.join(user_folder, file_name), 'wb') as f:
            f.write(downloaded_file)
            
        bot.reply_to(message, f"✅ وەرگیرا: {file_name}\n\n⚠️ تێبینی: لە Vercel ناتوانرێت بۆت بە بەردەوامی ڕەن بکرێت (Process Limit).")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, "⚠️ فەرمانەکە نەناسراوە.")

# --- Webhook Route for Vercel ---
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return 'Error', 403

@app.route('/')
def home():
    return "🚀 Bot is Running on Vercel!"

# Note: No app.run() needed, Vercel handles it via main.py

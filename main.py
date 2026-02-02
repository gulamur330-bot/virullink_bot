import os
import logging
import sqlite3
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- 1. CONFIGURATION ---
TOKEN = "7929473766:AAGrrDvLD_7VzyVAMZAGY4c0dKEtYyUJU_0"
ADMIN_ID = 8013042180

# --- 2. LOGGING (এরর দেখার জন্য) ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. FLASK SERVER (Render এ বোট বাঁচিয়ে রাখার জন্য) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is Running Stable on v21.10!"

def run_flask():
    # Render এর PORT ধরবে
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 4. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, title TEXT, invite_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, media_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 5. HELPERS ---
def get_db():
    return sqlite3.connect('bot_database.db')

# --- 6. HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"🔥 *হ্যালো {user.first_name}!* 🔥\n\n"
        "✅ বোট এখন লেটেস্ট ভার্সনে (v21) রান হচ্ছে!\n"
        "কোনো ক্র্যাশ ছাড়াই।\n\n"
        "👇 মেনু চেক করুন:",
        parse_mode=ParseMode.MARKDOWN
    )
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📂 Files", callback_data="files"), InlineKeyboardButton("🔗 Links", callback_data="links")],
        [InlineKeyboardButton("📞 Admin Panel", callback_data="admin_login")]
    ]
    await update.message.reply_text("👇 নিচে অপশন সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    kb = [
        [InlineKeyboardButton("📊 User Count", callback_data="stats")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_ch_dummy")]
    ]
    await update.message.reply_text("👑 *ADMIN PANEL* 👑", parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "stats":
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        await query.answer(f"📊 Total Users: {count}", show_alert=True)
    elif data == "admin_login":
        if query.from_user.id == ADMIN_ID:
            await admin_panel(update, context)
        else:
            await query.answer("❌ Only Admin Allowed!", show_alert=True)
    else:
        await query.answer("Working... 🔥", show_alert=True)

# --- 7. MAIN EXECUTION ---
def main():
    # 1. Flask আলাদা থ্রেডে চালানো (Daemon Mode)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # 2. Telegram Bot Setup
    print("🚀 Starting Bot with version 21.10...")
    application = Application.builder().token(TOKEN).build()

    # Handlers Add
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(button_handler))

    # 3. Polling Start (Drop Pending Updates to avoid conflict)
    # allowed_updates=Update.ALL_TYPES সব ধরনের মেসেজ রিসিভ করবে
    print("✅ Polling Started...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

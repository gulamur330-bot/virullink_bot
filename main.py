import os
import logging
import sqlite3
import threading
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- 1. CONFIGURATION ---
TOKEN = "7929473766:AAGrrDvLD_7VzyVAMZAGY4c0dKEtYyUJU_0"
ADMIN_ID = 8013042180

# --- 2. LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- 3. FLASK SERVER (For Render 24/7) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "😈 Bot is Live with Full Features! 24/7"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- 4. DATABASE ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, title TEXT, invite_link TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, media_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect('bot_database.db')

# --- 5. HELPERS & FORCE JOIN ---
async def check_force_join(user_id, context):
    """Check if user joined all forced channels"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT channel_id, title, invite_link FROM channels")
    channels = c.fetchall()
    conn.close()
    
    not_joined = []
    for ch_id, title, link in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked', 'banned']:
                not_joined.append({'title': title, 'link': link})
        except:
            # If bot is not admin or channel invalid, ignore or assume not joined
            pass 
    return not_joined

def get_welcome_data():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value, media_id FROM settings WHERE key='welcome'")
    data = c.fetchone()
    conn.close()
    return data if data else ("😈 Welcome to the Hot World! 😈", None)

# --- STATES ---
(TITLE, PHOTO, LINK, CONFIRM_POST, ADD_CH_ID, ADD_CH_LINK, WELCOME_PHOTO, WELCOME_TEXT) = range(8)

# --- 6. HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
    conn.commit()
    conn.close()
    
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    not_joined = await check_force_join(user.id, context)
    
    if not_joined:
        # Show Force Join Menu
        kb = []
        for ch in not_joined:
            kb.append([InlineKeyboardButton(f"🔥 Join {ch['title']}", url=ch['link'])])
        kb.append([InlineKeyboardButton("✅ Verify Now", callback_data="verify_join")])
        
        await update.message.reply_text(
            f"😈 *Hey {user.first_name}! Access Denied!* 🚫\n\n"
            "আমাদের হট কন্টেন্ট দেখতে হলে নিচের চ্যানেলগুলোতে Join করতে হবে!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb)
        )
    else:
        # Show Welcome / Main Menu
        text, media_id = get_welcome_data()
        caption = f"😈 *Hello {user.mention_html()}* 😈\n\n{text}"
        
        kb = [
            [InlineKeyboardButton("📂 Files", callback_data="files"), InlineKeyboardButton("🔗 Links", callback_data="links")],
            [InlineKeyboardButton("🔥 Updates", callback_data="updates"), InlineKeyboardButton("ℹ️ About", callback_data="about")],
            [InlineKeyboardButton("📞 Contact Admin", callback_data="contact")]
        ]
        
        if media_id:
            await context.bot.send_photo(chat_id=user.id, photo=media_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await context.bot.send_message(chat_id=user.id, text=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    not_joined = await check_force_join(user.id, context)
    
    if not_joined:
        await query.answer("❌ আপনি এখনও সব চ্যানেল Join করেননি!", show_alert=True)
    else:
        await query.answer("✅ Verification Successful! Welcome! 💖", show_alert=True)
        await query.message.delete()
        
        # Show Welcome Manually
        text, media_id = get_welcome_data()
        caption = f"😈 *Hello {user.mention_html()}* 😈\n\n{text}"
        kb = [
            [InlineKeyboardButton("📂 Files", callback_data="files"), InlineKeyboardButton("🔗 Links", callback_data="links")],
            [InlineKeyboardButton("🔥 Updates", callback_data="updates"), InlineKeyboardButton("ℹ️ About", callback_data="about")]
        ]
        if media_id:
            await context.bot.send_photo(chat_id=user.id, photo=media_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await context.bot.send_message(chat_id=user.id, text=caption, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

# --- ADMIN PANEL ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()

    text = f"👑 *Admin Panel* 👑\n\n📊 Total Users: `{total}`\nSelect Option:"
    kb = [
        [InlineKeyboardButton("📝 Multi-Post", callback_data="create_post"), InlineKeyboardButton("⚙️ Set Welcome", callback_data="set_welcome")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"), InlineKeyboardButton("➖ Del Channel", callback_data="del_channel_list")],
        [InlineKeyboardButton("❌ Close", callback_data="close_admin")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)

# --- POST WORKFLOW ---
async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📝 *Title* লিখুন (Hot Style):", parse_mode=ParseMode.MARKDOWN)
    return TITLE

async def post_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("❌ Title ফাঁকা রাখা যাবে না!")
        return TITLE
    context.user_data['p_title'] = update.message.text
    await update.message.reply_text("📸 *Media* (Photo/Video) দিন:")
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['p_media'] = update.message.photo[-1].file_id
        context.user_data['p_type'] = 'photo'
    elif update.message.video:
        context.user_data['p_media'] = update.message.video.file_id
        context.user_data['p_type'] = 'video'
    else:
        await update.message.reply_text("❌ Photo/Video দিতে হবে!")
        return PHOTO
    await update.message.reply_text("🔗 *Secret Link* দিন:")
    return LINK

async def post_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    if "http" not in link:
        await update.message.reply_text("❌ Invalid Link! আবার দিন।")
        return LINK
    context.user_data['p_link'] = link
    
    # Preview
    title = context.user_data['p_title']
    kb = [[InlineKeyboardButton("🔥 OPEN LINK 🔥", url=link)],
          [InlineKeyboardButton("✅ Confirm", callback_data="confirm_post"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")]]
    
    await update.message.reply_text("👀 *PREVIEW:*", parse_mode=ParseMode.MARKDOWN)
    if context.user_data['p_type'] == 'photo':
        await update.message.reply_photo(context.user_data['p_media'], caption=f"😈 {title}", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_video(context.user_data['p_media'], caption=f"😈 {title}", reply_markup=InlineKeyboardMarkup(kb))
    return CONFIRM_POST

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "cancel_post":
        await query.answer("❌ Cancelled")
        await query.message.delete()
        return ConversationHandler.END
    
    conn = get_db()
    channels = conn.execute("SELECT channel_id FROM channels").fetchall()
    conn.close()
    
    if not channels:
        await query.answer("❌ No channels found!", show_alert=True)
        return ConversationHandler.END

    title = context.user_data['p_title']
    media = context.user_data['p_media']
    link = context.user_data['p_link']
    
    caption = f"😈 {title} 😈\n\n🔥 *Hot Exclusive* 🔥\n👇👇👇"
    kb = [[InlineKeyboardButton("💋 WATCH VIDEO 💋", url=link)]]
    
    count = 0
    for ch in channels:
        try:
            if context.user_data['p_type'] == 'photo':
                await context.bot.send_photo(ch[0], photo=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await context.bot.send_video(ch[0], video=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
            count += 1
        except Exception as e:
            logger.error(f"Post failed for {ch[0]}: {e}")
            
    await query.answer(f"✅ Posted in {count} channels!", show_alert=True)
    await query.message.delete()
    return ConversationHandler.END

# --- ADD CHANNEL ---
async def start_add_ch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("🆔 Channel ID (-100...):")
    return ADD_CH_ID

async def get_ch_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ch_id'] = update.message.text
    await update.message.reply_text("🔗 Invite Link:")
    return ADD_CH_LINK

async def get_ch_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    conn.execute("INSERT INTO channels VALUES (?, ?, ?)", 
                 (context.user_data['ch_id'], "Hot Channel", update.message.text))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Channel Added!")
    return ConversationHandler.END

# --- WELCOME SETUP ---
async def start_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📸 Welcome Photo দিন (বা /skip):")
    return WELCOME_PHOTO

async def get_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['w_photo'] = update.message.photo[-1].file_id
    await update.message.reply_text("📝 Welcome Text (HTML allowed):")
    return WELCOME_TEXT

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['w_photo'] = None
    await update.message.reply_text("📝 Welcome Text (HTML allowed):")
    return WELCOME_TEXT

async def get_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    photo = context.user_data.get('w_photo')
    conn = get_db()
    conn.execute("REPLACE INTO settings (key, value, media_id) VALUES ('welcome', ?, ?)", (text, photo))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Welcome Message Updated!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END

# --- GLOBAL CALLBACKS ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "close_admin":
        await query.message.delete()
    elif data == "del_channel_list":
        conn = get_db()
        chs = conn.execute("SELECT channel_id, title FROM channels").fetchall()
        conn.close()
        kb = []
        for c in chs:
            kb.append([InlineKeyboardButton(f"🗑 {c[1]}", callback_data=f"del_{c[0]}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        await query.edit_message_text("Select channel to delete:", reply_markup=InlineKeyboardMarkup(kb))
    elif data.startswith("del_"):
        cid = data.split("_")[1]
        conn = get_db()
        conn.execute("DELETE FROM channels WHERE channel_id=?", (cid,))
        conn.commit()
        conn.close()
        await query.answer("✅ Deleted!", show_alert=True)
        await admin_panel(update, context)
    elif data == "admin_back":
        await admin_panel(update, context)
    elif data in ["files", "links", "updates"]:
        # Popup for locked content
        await query.answer("⚠️ Admin এখনও কন্টেন্ট যোগ করেননি!", show_alert=True)
    elif data == "contact":
        await query.answer("📞 Contact Admin for more info", show_alert=True)

# --- 7. MAIN RUNNER (Fixed for v21.10) ---
def main():
    # 1. Flask Thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # 2. Bot Setup
    print("🚀 Starting FULL FEATURED Bot...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    
    # Conversations
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_post, pattern="^create_post$")],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_title)],
            PHOTO: [MessageHandler(filters.PHOTO | filters.VIDEO, post_photo)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_link)],
            CONFIRM_POST: [CallbackQueryHandler(confirm_post, pattern="^(confirm_post|cancel_post)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_ch, pattern="^add_channel$")],
        states={
            ADD_CH_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ch_id)],
            ADD_CH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ch_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_welcome, pattern="^set_welcome$")],
        states={
            WELCOME_PHOTO: [MessageHandler(filters.PHOTO, get_welcome_photo), CommandHandler("skip", skip_photo)],
            WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_welcome_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    ))

    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # 3. Polling with v21 Fix
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()

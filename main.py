import logging
import sqlite3
import threading
import time
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)

# --- CONFIGURATION ---
TOKEN = "7929473766:AAGrrDvLD_7VzyVAMZAGY4c0dKEtYyUJU_0"
ADMIN_ID = 8013042180

# --- FLASK SERVER (FOR 24/7 RUN) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7! 🔥"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    # Force Join Channels Table
    c.execute('''CREATE TABLE IF NOT EXISTS channels (channel_id TEXT, title TEXT, invite_link TEXT)''')
    # Settings (Welcome Msg)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT, media_id TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- DATABASE HELPERS ---
def add_user(user_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def add_channel(c_id, title, link):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("INSERT INTO channels VALUES (?, ?, ?)", (c_id, title, link))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM channels")
    channels = c.fetchall()
    conn.close()
    return channels

def delete_channel(c_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_id=?", (c_id,))
    conn.commit()
    conn.close()

def set_welcome(text, photo_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("REPLACE INTO settings (key, value, media_id) VALUES ('welcome', ?, ?)", (text, photo_id))
    conn.commit()
    conn.close()

def get_welcome():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT value, media_id FROM settings WHERE key='welcome'")
    data = c.fetchone()
    conn.close()
    return data if data else ("Welcome to our Hot World! 😈🔥", None)

# --- STYLES & EMOJIS ---
STYLE_HEADER = "😈🔥 *PREMIUM ACCESS* 🔥😈\n\n"
STYLE_FOOTER = "\n\n🌹 *Stay Naughty, Stay Connected* 🌹"

# --- STATES FOR CONVERSATION ---
(
    TITLE, PHOTO, LINK, CONFIRM_POST, 
    ADD_CH_ID, ADD_CH_LINK, 
    SET_WELCOME_PHOTO, SET_WELCOME_TEXT
) = range(8)

# --- ADMIN DECORATOR ---
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# --- CHECK JOIN STATUS ---
async def check_join(user_id, context):
    channels = get_channels()
    not_joined = []
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=ch[0], user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append(ch)
        except:
            # Bot might not be admin, assume not joined or error
            not_joined.append(ch)
    return not_joined

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id)
    
    # Check Force Join
    not_joined = await check_join(user.id, context)
    
    if not_joined:
        keyboard = []
        for ch in not_joined:
            keyboard.append([InlineKeyboardButton(f"🔥 Join {ch[1]}", url=ch[2])])
        keyboard.append([InlineKeyboardButton("✅ Verify Now", callback_data="verify_join")])
        
        text = f"😈 *Hey {user.first_name}!* \n\n⚠️ *Access Denied!* \nআমাদের সব Hot Content দেখতে হলে নিচের চ্যানেলগুলোতে Join করতে হবে! 👇"
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await send_welcome(update, context)

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_data = get_welcome()
    caption = f"😈 *Hello {user.mention_html()}* 😈\n\n{welcome_data[0]}"
    
    keyboard = [
        [InlineKeyboardButton("📂 Naughty Files", callback_data="files"), InlineKeyboardButton("🔗 Secret Links", callback_data="links")],
        [InlineKeyboardButton("🔥 Hot Updates", callback_data="updates"), InlineKeyboardButton("ℹ️ About Me", callback_data="about")],
        [InlineKeyboardButton("📞 Contact Admin", callback_data="contact")]
    ]
    
    if welcome_data[1]: # If photo exists
        await context.bot.send_photo(chat_id=user.id, photo=welcome_data[1], caption=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await context.bot.send_message(chat_id=user.id, text=caption, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    not_joined = await check_join(user_id, context)
    
    if not_joined:
        await query.answer("❌ আপনি সব চ্যানেল Join করেননি! আবার চেক করুন।", show_alert=True)
    else:
        await query.answer("✅ Verification Successful! Welcome! 💖", show_alert=True)
        await query.message.delete()
        await send_welcome(update, context)

# --- ADMIN PANEL ---

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats"), InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📝 Multi-Post", callback_data="create_post"), InlineKeyboardButton("⚙️ Set Welcome", callback_data="setup_welcome")],
        [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"), InlineKeyboardButton("➖ Del Channel", callback_data="del_channel_list")],
        [InlineKeyboardButton("❌ Close", callback_data="close_admin")]
    ]
    text = "😈 *Admin Control Panel* 😈\n\nSelect an option to manage your 18+ Empire! 🔥"
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "stats":
        total = get_total_users()
        await query.answer(f"📊 Total Users: {total} 🔥", show_alert=True)
    
    elif data == "close_admin":
        await query.message.delete()

    elif data == "broadcast":
        await query.answer("⚠️ Broadcast feature requires async loop. (Added later)", show_alert=True)

    elif data == "del_channel_list":
        channels = get_channels()
        if not channels:
            await query.answer("❌ No channels found!", show_alert=True)
            return
        
        kb = []
        for ch in channels:
            kb.append([InlineKeyboardButton(f"🗑 {ch[1]}", callback_data=f"del_ch_{ch[0]}")])
        kb.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        await query.edit_message_text("Select channel to delete:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("del_ch_"):
        cid = data.split("_")[2]
        delete_channel(cid)
        await query.answer("✅ Channel Deleted!", show_alert=True)
        await admin_panel(update, context)

    elif data == "admin_back":
        await admin_panel(update, context)

    # Note: Complex flows like Add Channel/Post start via ConversationHandler below

# --- ADD CHANNEL CONVERSATION ---
async def start_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("🆔 Enter Channel ID (e.g., -100xxxx):")
    return ADD_CH_ID

async def get_ch_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ch_id'] = update.message.text
    await update.message.reply_text("🔗 Enter Channel Invite Link:")
    return ADD_CH_LINK

async def get_ch_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ch_link = update.message.text
    ch_id = context.user_data['ch_id']
    # Add dummy title or fetch it (Adding dummy for speed)
    add_channel(ch_id, "Hot Channel", ch_link)
    await update.message.reply_text("✅ Channel Added Successfully! 🔥")
    return ConversationHandler.END

# --- SET WELCOME CONVERSATION ---
async def start_set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📸 Send the Welcome PHOTO now (or send /skip):")
    return SET_WELCOME_PHOTO

async def get_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1].file_id
    context.user_data['wel_photo'] = photo
    await update.message.reply_text("📝 Now send the Welcome TEXT (HTML supported):")
    return SET_WELCOME_TEXT

async def skip_welcome_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['wel_photo'] = None
    await update.message.reply_text("📝 Now send the Welcome TEXT (HTML supported):")
    return SET_WELCOME_TEXT

async def get_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    photo = context.user_data.get('wel_photo')
    set_welcome(text, photo)
    await update.message.reply_text("✅ Welcome Message Updated! 💖")
    return ConversationHandler.END

# --- MULTI-POST SYSTEM (COMPLEX) ---
async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("📝 *Post Title* লিখুন (Hot Style):", parse_mode="Markdown")
    return TITLE

async def post_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text:
        await update.message.reply_text("❌ Title ফাঁকা রাখা যাবে না! আবার লিখুন।")
        return TITLE
    context.user_data['p_title'] = update.message.text
    await update.message.reply_text("📸 *Photo* বা *Video* দিন:", parse_mode="Markdown")
    return PHOTO

async def post_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['p_media'] = update.message.photo[-1].file_id
        context.user_data['p_type'] = 'photo'
    elif update.message.video:
        context.user_data['p_media'] = update.message.video.file_id
        context.user_data['p_type'] = 'video'
    else:
        await update.message.reply_text("❌ দয়া করে Photo বা Video দিন!")
        return PHOTO
    
    await update.message.reply_text("🔗 *Post Link* দিন (যেখানে ইউজারকে নেওয়া হবে):", parse_mode="Markdown")
    return LINK

async def post_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    if "http" not in link:
        await update.message.reply_text("❌ Invalid Link! 'http' থাকতে হবে। আবার দিন।")
        return LINK
    context.user_data['p_link'] = link
    
    # Preview
    title = context.user_data['p_title']
    media = context.user_data['p_media']
    
    kb = [[InlineKeyboardButton("🔥 CLICK HERE TO WATCH 🔥", url=link)]]
    kb.append([InlineKeyboardButton("✅ Confirm & Post", callback_data="confirm_post"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")])
    
    caption = f"😈 {title} 😈\n\n👇👇👇"
    
    await update.message.reply_text("👀 *PREVIEW:*", parse_mode="Markdown")
    
    if context.user_data['p_type'] == 'photo':
        await update.message.reply_photo(photo=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_video(video=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
        
    return CONFIRM_POST

async def confirm_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "cancel_post":
        await query.answer("❌ Post Cancelled!", show_alert=True)
        await query.message.delete()
        return ConversationHandler.END
    
    # Send to Channels
    channels = get_channels()
    if not channels:
        await query.answer("❌ No channels set to post!", show_alert=True)
        return ConversationHandler.END
        
    title = context.user_data['p_title']
    media = context.user_data['p_media']
    link = context.user_data['p_link']
    m_type = context.user_data['p_type']
    
    caption = f"😈 {title} 😈\n\n🔞 *Full Video/Files:* 👇\n{link}\n\n🔥 *Enjoy & Share* 🔥"
    kb = [[InlineKeyboardButton("💋 OPEN LINK 💋", url=link)]]
    
    count = 0
    for ch in channels:
        try:
            if m_type == 'photo':
                await context.bot.send_photo(chat_id=ch[0], photo=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
            else:
                await context.bot.send_video(chat_id=ch[0], video=media, caption=caption, reply_markup=InlineKeyboardMarkup(kb))
            count += 1
        except Exception as e:
            print(f"Failed to send to {ch[0]}: {e}")
            
    await query.answer(f"✅ Sent to {count} channels!", show_alert=True)
    await query.message.delete()
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action Cancelled.")
    return ConversationHandler.END

# --- MAIN EXECUTION ---

def main():
    # Keep Alive Thread
    threading.Thread(target=run_flask).start()
    
    # Telegram Bot
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(stats|broadcast|del_channel_list|close_admin|admin_back|del_ch_)"))

    # Conversations
    # 1. Post System
    post_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_post, pattern="^create_post$")],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_title)],
            PHOTO: [MessageHandler(filters.PHOTO | filters.VIDEO, post_photo)],
            LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_link)],
            CONFIRM_POST: [CallbackQueryHandler(confirm_post_handler, pattern="^(confirm_post|cancel_post)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )
    
    # 2. Add Channel
    add_ch_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_channel, pattern="^add_channel$")],
        states={
            ADD_CH_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ch_id)],
            ADD_CH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ch_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )
    
    # 3. Set Welcome
    wel_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_set_welcome, pattern="^setup_welcome$")],
        states={
            SET_WELCOME_PHOTO: [
                MessageHandler(filters.PHOTO, get_welcome_photo),
                CommandHandler("skip", skip_welcome_photo)
            ],
            SET_WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_welcome_text)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)]
    )

    app.add_handler(post_conv)
    app.add_handler(add_ch_conv)
    app.add_handler(wel_conv)

    print("🔥 Bot is Running in 18+ Mode...")
    app.run_polling()

if __name__ == "__main__":
    main()

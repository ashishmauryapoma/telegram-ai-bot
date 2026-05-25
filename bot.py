import os
import json
from datetime import datetime

from groq import Groq

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# ENV VARIABLES
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# =========================
# ADMIN CONFIG
# =========================

ADMIN_ID = 7239128382  # 🔴 CHANGE THIS to your Telegram ID

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

# =========================
# FILE STORAGE
# =========================

MEMORY_FILE = "memory.json"

if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        user_memory = json.load(f)
else:
    user_memory = {}

# =========================
# USER TRACKING
# =========================

user_stats = {}

# =========================
# SAVE MEMORY
# =========================

def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_memory, f, indent=4)

# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Welcome to AI Bot!\n\nSend me a message to chat."
    )

# =========================
# RESET MEMORY
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id in user_memory:
        del user_memory[user_id]
        save_memory()

    await update.message.reply_text("🧠 Your memory has been reset.")

# =========================
# ADMIN STATS
# =========================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Not authorized")
        return

    total_users = len(user_stats)
    total_messages = sum(u["messages"] for u in user_stats.values())

    await update.message.reply_text(
        f"📊 BOT STATS\n\n"
        f"👥 Users: {total_users}\n"
        f"💬 Messages: {total_messages}"
    )

# =========================
# USER LIST
# =========================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Not authorized")
        return

    text = "👤 USERS LIST\n\n"

    for uid, data in user_stats.items():
        text += f"- {data['username']} | {data['messages']} msgs\n"

    await update.message.reply_text(text or "No users yet.")

# =========================
# BROADCAST
# =========================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not is_admin(user_id):
        await update.message.reply_text("❌ Not authorized")
        return

    message = " ".join(context.args)

    if not message:
        await update.message.reply_text("Usage: /broadcast your message")
        return

    for uid in user_stats:
        try:
            await context.bot.send_message(chat_id=uid, text=message)
        except:
            pass

    await update.message.reply_text("📢 Broadcast sent!")

# =========================
# MAIN CHAT HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "unknown"
    message = update.message.text

    # -------------------------
    # TRACK USER
    # -------------------------

    if user_id not in user_stats:
        user_stats[user_id] = {
            "username": username,
            "messages": 0,
            "last_active": str(datetime.now())
        }

    user_stats[user_id]["messages"] += 1
    user_stats[user_id]["last_active"] = str(datetime.now())

    # -------------------------
    # MEMORY INIT
    # -------------------------

    if user_id not in user_memory:
        user_memory[user_id] = [
            {
                "role": "system",
                "content": "You are a friendly AI chatbot. Keep answers short, helpful, and natural."
            }
        ]

    user_memory[user_id].append({
        "role": "user",
        "content": message
    })

    user_memory[user_id] = user_memory[user_id][-20:]

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=user_memory[user_id]
        )

        reply = response.choices[0].message.content

        user_memory[user_id].append({
            "role": "assistant",
            "content": reply
        })

        save_memory()

        await update.message.reply_text(reply)

    except Exception as e:
        print(e)
        await update.message.reply_text("⚠️ AI error occurred.")

# =========================
# BOT SETUP
# =========================

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))

# Admin commands
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("users", users))
app.add_handler(CommandHandler("broadcast", broadcast))

# Messages
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 AI Bot with Admin Panel is running...")

app.run_polling()
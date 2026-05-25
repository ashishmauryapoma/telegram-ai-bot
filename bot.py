import os
import json
from datetime import datetime
from threading import Thread

from flask import Flask
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
# FLASK APP (IMPORTANT FOR RENDER)
# =========================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 Telegram AI Bot is Running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=10000)

Thread(target=run_flask).start()

# =========================
# ADMIN SETUP
# =========================

ADMIN_ID = 7239128382  # 🔴 replace with your Telegram ID

def is_admin(user_id):
    return int(user_id) == ADMIN_ID

# =========================
# STORAGE
# =========================

MEMORY_FILE = "memory.json"

if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
else:
    memory = {}

user_stats = {}

def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=4)

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 AI Bot is active! Chat with me.")

# =========================
# RESET
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    if uid in memory:
        del memory[uid]
        save_memory()

    await update.message.reply_text("🧠 Memory cleared!")

# =========================
# ADMIN STATS
# =========================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Not allowed")
        return

    total_users = len(user_stats)
    total_msgs = sum(u["messages"] for u in user_stats.values())

    await update.message.reply_text(
        f"📊 STATS\n\n👥 Users: {total_users}\n💬 Messages: {total_msgs}"
    )

# =========================
# USER TRACKING
# =========================

def track_user(uid, username):
    if uid not in user_stats:
        user_stats[uid] = {
            "username": username,
            "messages": 0,
            "last_active": str(datetime.now())
        }

    user_stats[uid]["messages"] += 1
    user_stats[uid]["last_active"] = str(datetime.now())

# =========================
# MAIN CHAT
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = str(update.message.from_user.id)
    username = update.message.from_user.username or "unknown"
    msg = update.message.text

    track_user(uid, username)

    if uid not in memory:
        memory[uid] = [
            {
                "role": "system",
                "content": "You are a friendly AI chatbot. Keep answers short and helpful."
            }
        ]

    memory[uid].append({"role": "user", "content": msg})
    memory[uid] = memory[uid][-20:]

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=memory[uid]
        )

        reply = response.choices[0].message.content

        memory[uid].append({"role": "assistant", "content": reply})
        save_memory()

        await update.message.reply_text(reply)

    except Exception as e:
        print(e)
        await update.message.reply_text("⚠️ AI error")

# =========================
# BOT SETUP
# =========================

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("stats", stats))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Bot + Flask running...")

app.run_polling()
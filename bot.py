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

# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ==========================================
# PASSWORD
# ==========================================

BOT_PASSWORD = "Ashish"

# ==========================================
# GROQ CLIENT
# ==========================================

client = Groq(api_key=GROQ_API_KEY)

# ==========================================
# FILES
# ==========================================

MEMORY_FILE = "memory.json"
CHAT_LOG_FILE = "chat_history.txt"

# ==========================================
# LOAD MEMORY
# ==========================================

if os.path.exists(MEMORY_FILE):

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        user_conversations = json.load(f)

else:
    user_conversations = {}

# ==========================================
# AUTHENTICATED USERS
# ==========================================

authenticated_users = set()

# ==========================================
# SAVE MEMORY
# ==========================================


def save_memory():

    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(user_conversations, f, ensure_ascii=False, indent=4)

# ==========================================
# START COMMAND
# ==========================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔐 Welcome to AI Chat Bot!\n\n"
        "Please enter the password to continue."
    )

# ==========================================
# RESET COMMAND
# ==========================================


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)

    if user_id in user_conversations:
        del user_conversations[user_id]
        save_memory()

    await update.message.reply_text(
        "🧠 Memory reset successfully."
    )

# ==========================================
# MAIN MESSAGE HANDLER
# ==========================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username
    user_message = update.message.text

    # ==========================================
    # PASSWORD CHECK
    # ==========================================

    if user_id not in authenticated_users:

        if user_message == BOT_PASSWORD:

            authenticated_users.add(user_id)

            await update.message.reply_text(
                "✅ Password correct!\n\n"
                "You can now chat with the AI 🤖"
            )

        else:

            await update.message.reply_text(
                "❌ Wrong password. Try again."
            )

        return

    # ==========================================
    # CREATE MEMORY FOR NEW USER
    # ==========================================

    if user_id not in user_conversations:

        user_conversations[user_id] = [
            {
                "role": "system",
                "content": """
You are a friendly AI chatbot.

Rules:
- Be friendly and conversational
- Answer general questions clearly
- Keep replies simple and natural
- Use emojis occasionally
- Be helpful and engaging
"""
            }
        ]

    # ==========================================
    # SAVE USER MESSAGE
    # ==========================================

    user_conversations[user_id].append(
        {
            "role": "user",
            "content": user_message
        }
    )

    # Keep only recent messages
    user_conversations[user_id] = user_conversations[user_id][-20:]

    try:

        # ==========================================
        # AI RESPONSE
        # ==========================================

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=user_conversations[user_id]
        )

        ai_reply = response.choices[0].message.content

        # ==========================================
        # SAVE AI RESPONSE
        # ==========================================

        user_conversations[user_id].append(
            {
                "role": "assistant",
                "content": ai_reply
            }
        )

        save_memory()

        # ==========================================
        # CHAT LOGGING
        # ==========================================

        with open(CHAT_LOG_FILE, "a", encoding="utf-8") as file:

            current_time = datetime.now().strftime(
                "%Y-%m-%d %I:%M %p"
            )

            file.write(f"\n[{current_time}]\n")
            file.write(f"User ({username}): {user_message}\n")
            file.write(f"Bot: {ai_reply}\n")
            file.write("-" * 50 + "\n")

        # ==========================================
        # SEND REPLY
        # ==========================================

        await update.message.reply_text(ai_reply)

    except Exception as e:

        print("ERROR:", e)

        await update.message.reply_text(
            "⚠️ AI error occurred. Please try again later."
        )

# ==========================================
# BUILD BOT
# ==========================================

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# Commands
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))

# Messages
app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("🤖 AI Chat Bot is running...")

# ==========================================
# START BOT
# ==========================================

app.run_polling()
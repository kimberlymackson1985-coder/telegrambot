import os
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TOKEN")

bot_username = "YourBotUsername"
ADMIN_ID = 123456789  # replace with your Telegram ID

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER,
    referrals INTEGER,
    accepted_policy INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    product TEXT,
    status TEXT
)
""")

conn.commit()

# ---------------- HELPERS ----------------
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def create_user(user_id):
    if not get_user(user_id):
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user_id, 0, 0, 0))
        conn.commit()

# ---------------- START ----------------
def start(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    args = context.args

    create_user(user_id)

    if args:
        ref_id = args[0].replace("ref_", "")
        if ref_id != user_id and get_user(ref_id):
            cursor.execute("""
                UPDATE users 
                SET referrals = referrals + 1, balance = balance + 5 
                WHERE user_id=?
            """, (ref_id,))
            conn.commit()

    keyboard = [
        ["💵 WALLET", "🛒 STORE"],
        ["🔗 REFERRAL", "🏆 LEADERBOARD"],
        ["📜 POLICY", "📦 ORDERS"]
    ]

    update.message.reply_text(
        "🔥 Welcome to Pro Shop Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- PRODUCTS ----------------
products = {
    "vip": 50,
    "gold": 80,
    "basic": 10
}

# ---------------- FEATURES ----------------
def wallet(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    user = get_user(user_id)

    update.message.reply_text(f"💵 WALLET\n\nBalance: {user[1]} USDT\nReferrals: {user[2]}")

def referral(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    update.message.reply_text(f"🔗 Referral Link:\n{link}")

def policy(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    cursor.execute("UPDATE users SET accepted_policy=1 WHERE user_id=?", (user_id,))
    conn.commit()

    update.message.reply_text("📜 Policy accepted ✅")

def store(update: Update, context: CallbackContext):
    msg = "🛒 STORE\n\n"
    for k, v in products.items():
        msg += f"{k.upper()} - {v} USDT\n"
    update.message.reply_text(msg)

def orders(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)

    cursor.execute("SELECT product, status FROM orders WHERE user_id=?", (user_id,))
    data = cursor.fetchall()

    if not data:
        update.message.reply_text("📦 No orders yet.")
        return

    msg = "📦 ORDERS\n\n"
    for d in data:
        msg += f"{d[0]} - {d[1]}\n"

    update.message.reply_text(msg)

def leaderboard(update: Update, context: CallbackContext):
    cursor.execute("SELECT user_id, referrals FROM users ORDER BY referrals DESC LIMIT 5")
    data = cursor.fetchall()

    msg = "🏆 LEADERBOARD\n\n"
    rank = 1

    for d in data:
        msg += f"{rank}. {d[0]} - {d[1]} refs\n"
        rank += 1

    update.message.reply_text(msg)

# ---------------- MESSAGE HANDLER ----------------
def handle(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    text = update.message.text.lower()

    create_user(user_id)
    user = get_user(user_id)

    if text == "💵 wallet":
        wallet(update, context)

    elif text == "🔗 referral":
        referral(update, context)

    elif text == "📜 policy":
        policy(update, context)

    elif text == "🛒 store":
        store(update, context)

    elif text == "🏆 leaderboard":
        leaderboard(update, context)

    elif text == "📦 orders":
        orders(update, context)

    elif text in products:
        if user[3] == 0:
            update.message.reply_text("❌ Accept policy first")
            return

        price = products[text]

        if user[1] >= price:
            cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
            cursor.execute("INSERT INTO orders (user_id, product, status) VALUES (?, ?, ?)", (user_id, text, "completed"))
            conn.commit()

            update.message.reply_text(f"✅ Purchased {text.upper()}")
        else:
            update.message.reply_text("❌ Not enough balance")

# ---------------- MAIN ----------------
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()


import telebot
from telebot import types
import random
import sqlite3
import time
import os

API_TOKEN = os.getenv("BOT_TOKEN", "7725236439:AAFmEBPAFZapIs7mBrFIQwWXHaZrpY0T1zY")
CHANNEL_USERNAME = "@housebrawlnews"
ADMIN_ID = 7803143441

bot = telebot.TeleBot(API_TOKEN)
conn = sqlite3.connect('brawlbot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gems REAL DEFAULT 0,
    last_box INTEGER DEFAULT 0,
    ref_id INTEGER,
    referrals INTEGER DEFAULT 0,
    boxes_opened INTEGER DEFAULT 0
)
''')
conn.commit()

def check_subscription(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    args = message.text.split()
    ref_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (user_id, ref_id) VALUES (?, ?)", (user_id, ref_id))
        conn.commit()
        if ref_id and ref_id != user_id:
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (ref_id,))
            cursor.execute("UPDATE users SET boxes_opened = boxes_opened + 1 WHERE user_id=?", (ref_id,))
            conn.commit()

    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("✅ Я подписался", callback_data="check_sub"))
        bot.send_message(user_id, "🔒 Подпишись на канал, чтобы пользоваться ботом:", reply_markup=markup)
    else:
        show_main_menu(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check(call):
    if check_subscription(call.from_user.id):
        show_main_menu(call.from_user.id)
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписались!")

def show_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎁 Открыть бокс", "👤 Профиль", "🏆 Лидерборд", "📤 Вывод")
    bot.send_message(user_id, "Добро пожаловать! Выбери действие:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🎁 Открыть бокс")
def open_box(message):
    user_id = message.from_user.id
    now = int(time.time())

    cursor.execute("SELECT last_box FROM users WHERE user_id=?", (user_id,))
    last_box = cursor.fetchone()[0]

    if now - last_box < 3 * 60 * 60:
        remaining = 3 * 60 * 60 - (now - last_box)
        minutes = remaining // 60
        bot.send_message(user_id, f"⏳ Следующий бокс будет доступен через {minutes} мин.")
        return

    reward = 0.01 if random.random() < 0.99 else 10
    cursor.execute("UPDATE users SET gems = gems + ?, last_box = ?, boxes_opened = boxes_opened + 1 WHERE user_id=?", (reward, now, user_id))
    conn.commit()
    bot.send_message(user_id, f"🎉 Вы открыли бокс и получили {reward} гемов!")

@bot.message_handler(func=lambda msg: msg.text == "👤 Профиль")
def profile(message):
    user_id = message.from_user.id
    cursor.execute("SELECT gems, referrals, boxes_opened FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if result:
        gems, referrals, boxes = result
        ref_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        bot.send_message(user_id, f"👤 Профиль:
💎 Гемы: {gems:.2f}
📦 Боксов открыто: {boxes}
👥 Рефералы: {referrals}
🔗 Ссылка: {ref_link}")
    else:
        bot.send_message(user_id, "Напиши /start для регистрации")

@bot.message_handler(func=lambda msg: msg.text == "🏆 Лидерборд")
def leaderboard(message):
    cursor.execute("SELECT user_id, boxes_opened FROM users ORDER BY boxes_opened DESC LIMIT 10")
    top = cursor.fetchall()
    text = "🏆 Топ по открытиям:
"
    for i, (uid, count) in enumerate(top, 1):
        text += f"{i}. ID {uid} — {count} боксов
"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.text == "📤 Вывод")
def withdraw(message):
    user_id = message.from_user.id
    cursor.execute("SELECT gems FROM users WHERE user_id=?", (user_id,))
    gems = cursor.fetchone()[0]
    if gems < 30:
        bot.send_message(user_id, "❌ Для вывода нужно минимум 30 гемов.")
        return
    bot.send_message(user_id, "✅ Запрос на вывод отправлен. Админ свяжется с вами.")
    bot.send_message(ADMIN_ID, f"📤 Пользователь ID {user_id} запросил вывод {gems:.2f} гемов.")

bot.infinity_polling()

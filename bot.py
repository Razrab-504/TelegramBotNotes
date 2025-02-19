import telebot
from telebot import types
import sqlite3
from functools import partial

db = sqlite3.connect("base_data.db")
cur = db.cursor()

names = None

cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        note_name TEXT,
        note_text TEXT
    )
""")
db.commit()
db.close()

token = "token"
bot = telebot.TeleBot(token = token)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("Создать заметку", callback_data="create_note")
    btn2 = types.InlineKeyboardButton("Просмотреть заметки", callback_data="view_notes")
    btn3 = types.InlineKeyboardButton("Удалить заметку", callback_data="delete_note")
    
    markup.add(btn1, btn2, btn3)

    bot.send_message(message.chat.id, "Привет! 👋\nЯ QuantumNotebot — твой личный помощник для создания и хранения заметок прямо в Telegram. Вот что я умею:\n\n1) Создавать новые заметки ✍️\n2) Просматривать все твои заметки 📑\n3) Редактировать заметки 🛠️\n4) Удалять ненужные заметки 🗑️\n\nЧтобы начать, выбери одну из опций ниже:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "delete_note")
def delete(call):
    global names
    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()
        cur.execute("SELECT note_name FROM notes WHERE user_id = ?", (call.message.chat.id,))
        names = cur.fetchall()
        
        if not names:
            bot.send_message(call.message.chat.id, "У вас нет записей.")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        for note in names:
            note_name = note[0]
            btn = types.InlineKeyboardButton(note_name, callback_data=f"delete_{note_name}")
            markup.add(btn)

        bot.send_message(call.message.chat.id, "Выберите заметку для удаления:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_notes(call):
    note_name = call.data[7:]

    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()
        cur.execute("DELETE FROM notes WHERE user_id = ? AND note_name = ?", (call.message.chat.id, note_name))
        db.commit()

    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("Запустить бота заново", callback_data="restart")
    markup.add(btn)

    bot.send_message(call.message.chat.id, f"Вы успешно удалили заметку '{note_name}'", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "view_notes")
def view_notes_callback(call):
    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()
        cur.execute("SELECT note_name FROM notes WHERE user_id = ?", (call.message.chat.id,))
        names = cur.fetchall()
        info = ''
        if not names:
            bot.send_message(call.message.chat.id, "У вас нет записей")

        markup = types.InlineKeyboardMarkup(row_width=2)
        for note in names:
            note_name = note[0]
            btn = types.InlineKeyboardButton(note_name, callback_data=f"show_{note_name}")
            markup.add(btn)

        bot.send_message(call.message.chat.id, "Выберите заметку, чтобы увидеть её содержимое:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("show_"))
def show_text(call):
    note_name = call.data[5:]

    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()
        cur.execute("SELECT note_text FROM notes WHERE user_id = ? AND note_name = ?", (call.message.chat.id, note_name))
        note_text = cur.fetchone()

    txt = ""

    for el in note_text:
        txt += el

    if note_text:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("Запустить заново бота!!", callback_data="restart")
        markup.add(btn)
        
        bot.send_message(call.message.chat.id, f"Содержимое заметки '{note_name}':\n\n{txt}", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, f"В заметке '{note_name}' нет содержимого")


@bot.callback_query_handler(func=lambda call: call.data == "create_note")
def create_note_callback(call):
    bot.send_message(call.message.chat.id, "Отправьте название вашей заметки 📑")
    bot.register_next_step_handler(call.message, name)

def name(message):
    note_name = message.text.strip()
    user_id = message.chat.id

    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()

        cur.execute("SELECT COUNT(*) FROM notes WHERE user_id = ? AND note_name = ?", (user_id, note_name))
        if cur.fetchone()[0] > 0:
            bot.send_message(message.chat.id, f"Заметка с названием '{note_name}' уже существует! Пожалуйста, выберите другое название.")
            return

        cur.execute("INSERT INTO notes (user_id, note_name) VALUES (?, ?)", (user_id, note_name))
        db.commit()

    bot.send_message(message.chat.id, f"Заметка с названием '{note_name}' успешно создана! Теперь отправьте текст заметки.")
    bot.register_next_step_handler(message, partial(text, note_name=note_name))


def text(message, note_name):
    text_note = message.text.strip()
    user_id = message.chat.id

    with sqlite3.connect("base_data.db") as db:
        cur = db.cursor()

        cur.execute("SELECT COUNT(*) FROM notes WHERE user_id = ? AND note_name = ? AND note_text = ?", 
                    (user_id, note_name, text_note))
        
        result = cur.fetchone()

        if result and result[0] > 0:
            bot.send_message(message.chat.id, "Заметка с таким текстом уже существует! Попробуйте другой текст.")
            return
        else:
            cur.execute("UPDATE notes SET note_text = ? WHERE user_id = ? AND note_name = ?", 
                        (text_note, user_id, note_name))
            db.commit()

    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("Запустить бота снова!", callback_data="restart")
    markup.add(btn1)

    bot.send_message(message.chat.id, f"Текст для заметки '{note_name}' сохранен! Нажмите на кнопку и запустите бота снова!", reply_markup=markup)




@bot.callback_query_handler(func=lambda call: call.data == "restart")
def restart(call):
    start(call.message)


bot.infinity_polling()

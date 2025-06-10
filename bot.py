import telebot
from telebot import types
from config import BOT_TOKEN, CHANNEL_USERNAME
from database import init_db, add_user, get_balance, get_referrals, update_balance, user_exists

bot = telebot.TeleBot(BOT_TOKEN)
init_db()

pending_referrals = {}
ADMINS = [7236220432,5660220707] 

admin_states = {}
temp_data = {}

@bot.message_handler(commands=['start'])
def start_handler(message):


    user_id = message.from_user.id
    args = message.text.split()

    if len(args) > 1 and args[1].isdigit():
        pending_referrals[user_id] = int(args[1])
    else:
        pending_referrals[user_id] = None

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}"))
    markup.add(types.InlineKeyboardButton("🔁 Я подписался", callback_data="check_sub"))
    bot.send_message(user_id, "Пожалуйста, подпишитесь на канал 👇", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription(call):
    user_id = call.from_user.id
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            raise Exception("Not subscribed")

        invited_by = pending_referrals.get(user_id)
        if invited_by == user_id:
            invited_by = None

        add_user(user_id, invited_by)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎯 Моя реф. ссылка", "👥 Мои рефералы", "💰 Мой баланс", "💱 Вывод", "❗️ Правила")
        if user_id in ADMINS:
            markup.add("🛠 Админ панель")

        bot.send_message(user_id, "✅ Вы успешно подписались!", reply_markup=markup)
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Ошибка при проверке подписки пользователя {user_id}: {e}")
        bot.send_message(user_id, "❌ Вы ещё не подписались. Подпишитесь на канал и нажмите кнопку снова.")
        bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda m: m.text == "❗️ Правила")
def rules(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "❗️ Ознакомьтесь с правилами: https://telegra.ph/Oficialnye-Pravila-ispolzovaniya-referalnogo-bota-Growgardenref-botWhitencode-06-10")

@bot.message_handler(func=lambda m: m.text == "🎯 Моя реф. ссылка")
def ref_link(message):
    user_id = message.from_user.id
    link = f"https://t.me/{bot.get_me().username}?start={user_id}"
    bot.send_message(user_id, f"🎯 Ваша реферальная ссылка:\n{link}\n💸 1 реферал = 100 миллионов валюты Grow a garden\n Вывод доступен от 10 рефералов.")

@bot.message_handler(func=lambda m: m.text == "👥 Мои рефералы")
def my_refs(message):
    user_id = message.from_user.id
    refs = get_referrals(user_id)
    if refs:
        bot.send_message(user_id, f"Вы пригласили {len(refs)} человек(а):\n" + "\n".join(refs))
    else:
        bot.send_message(user_id, "У вас пока нет рефералов.")

@bot.message_handler(func=lambda m: m.text == "💱 Вывод")
def wiwod(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "💱 Отправьте скриншот баланса в лс @snekyys для вывода средств.")

@bot.message_handler(func=lambda m: m.text == "💰 Мой баланс")
def my_balance(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    bot.send_message(user_id, f"💰 Ваш баланс: {balance:,} монет")

# Админка

@bot.message_handler(func=lambda m: m.text == "🛠 Админ панель")
def admin_panel(message):
    if message.from_user.id not in ADMINS:
        return bot.send_message(message.chat.id, "❌ У вас нет доступа.")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 Проверить баланс", "➕ Начислить", "➖ Списать", "🔙 Назад")
    bot.send_message(message.chat.id, "⚙️ Админ панель", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🔍 Проверить баланс", "➕ Начислить", "➖ Списать"])
def handle_admin_action(message):
    if message.from_user.id not in ADMINS:
        return
    admin_states[message.from_user.id] = message.text
    bot.send_message(message.chat.id, "Введите ID пользователя:")

@bot.message_handler(func=lambda m: m.from_user.id in admin_states)
def process_admin_action(message):
    admin_id = message.from_user.id
    action = admin_states[admin_id]

    if admin_id in temp_data and "user_id" in temp_data[admin_id]:
        try:
            amount = int(message.text)
            user_id = temp_data[admin_id]["user_id"]
            if not user_exists(user_id):
                bot.send_message(admin_id, "❌ Пользователь не найден в базе.")
            else:
                if action == "➕ Начислить":
                    update_balance(user_id, amount)
                    bot.send_message(admin_id, f"✅ Начислено {amount} монет пользователю {user_id}.")
                elif action == "➖ Списать":
                    update_balance(user_id, -amount)
                    bot.send_message(admin_id, f"✅ Списано {amount} монет у пользователя {user_id}.")
            temp_data.pop(admin_id)
            admin_states.pop(admin_id)
        except ValueError:
            bot.send_message(admin_id, "Введите корректное число.")
    else:
        try:
            user_id = int(message.text)
            temp_data[admin_id] = {"user_id": user_id}
            if action == "🔍 Проверить баланс":
                if not user_exists(user_id):
                    bot.send_message(admin_id, "❌ Пользователь не найден.")
                else:
                    balance = get_balance(user_id)
                    bot.send_message(admin_id, f"💰 Баланс пользователя {user_id}: {balance} монет")
                admin_states.pop(admin_id)
                temp_data.pop(admin_id, None)
            else:
                bot.send_message(admin_id, "Введите сумму:")
        except ValueError:
            bot.send_message(admin_id, "Введите корректный ID.")

print("Бот запущен.")
bot.infinity_polling()


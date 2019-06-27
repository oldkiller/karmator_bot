#!usr/bin/python3
import datetime
import hashlib
import string
import os

from flask import Flask, request
import peewee as pw
import telebot

from database import KarmaUser, Limitation
import config


TELEGRAM_API = os.environ["telegram_token"]
bot = telebot.TeleBot(TELEGRAM_API)


def is_my_message(msg):
	"""
	Функция для проверки, какому боту отправлено сообщение.
	Для того, чтобы не реагировать на команды для других ботов.
	"""
	text = msg.text.split()[0].split("@")
	if len(text) > 1:
		if text[1] != config.bot_name:
			return False
	return True


@bot.message_handler(commands=["start"], func=is_my_message)
def start(msg):
	reply_text = (
			"Здравствуйте, я бот, который отвечает за " +
			" подсчет кармы в групповых чатах.")
	bot.send_message(msg.chat.id, reply_text)


@bot.message_handler(commands=["help"], func=is_my_message)
def helps(msg):
	help_mess = "Правила работы бота:\
	\n0. Выражения похвалы повышают карму, ругательства понижают.\
	\n1. Ограничения на выдачу кармы: 7 раз в 12 часов.\
	\n2. Можно заморозить свою карму.\
	При этом ограничивается и выдача, и получение.\
	\nДоступны следующие комманды:\
	\n/mykarm Для просмотра своей кармы.\
	\n/topbest Для того, что-бы узнать наиболее благодаримых в этом чате. \
	\n/topbad Для того, что-бы узнать наиболее ругаемых в этом чате.\
	\n/freezeme Для заморозки своей кармы.\
	\n/unfreezeme Для разморозки своей кармы.\
	\n/source Ссылка на GitHub репозиторий."
	bot.send_message(msg.chat.id, help_mess)


@bot.message_handler(commands=["source"], func=is_my_message)
def source(msg):
	"""
	Функция, которая по запросу возвращает ссылку на гитхаб-репозиторий,
	в котором хранится исходный код бота
	"""
	reply_text = "Исходный код доступен по ссылке: " + config.source_link
	bot.send_message(msg.chat.id, reply_text)


def select_user(user, chat):
	"""
	Функция для извлечения данных о пользователе \n
	user - пользователь, данные которого необходимы \n
	chat - чат, в котором находится пользователь
	TODO
	"""
	selected_user = KarmaUser.select().where(
		(KarmaUser.userid == user.id) &
		(KarmaUser.chatid == chat.id)).get()
	return selected_user


def insert_user(user, chat):
	"""
	Функция для добавления нового пользователя \n
	user - данные добавляемого пользователя \n
	chat - чат, в котором находится пользователь
	TODO
	"""
	new_user = KarmaUser.create(
				userid=user.id,
				chatid=chat.id,
				karma=0,
				user_name=(user.first_name or "") + (user.last_name or ""),
				user_nick=user.username or "",
				is_freezed=False)
	new_user.save()


def change_karma(user, chat, result):
	"""
	Функция для изменения значения кармы пользователя
	user - пользователь, которому нужно изменить карму \n
	chat - чат, в котором находится пользователь \n
	result - насколько нужно изменить карму
	"""
	selected_user = KarmaUser.select().where(
		(KarmaUser.chatid == chat.id) &
		(KarmaUser.userid == user.id))

	if not selected_user:
		insert_user(user, chat)
	user_name = (user.first_name or "") + (user.last_name or "")
	user_nick = user.username or ""
	update_user = KarmaUser.update(
							karma=(KarmaUser.karma + result),
							user_name=user_name,
							user_nick=user_nick
						).where(
							(KarmaUser.userid == user.id) &
							(KarmaUser.chatid == chat.id))
	update_user.execute()


@bot.message_handler(commands=["mykarm"], func=is_my_message)
def my_karma(msg):
	"""
	Функция, которая выводит значение кармы для пользователя.
	Выводится карма для пользователя, который вызвал функцию
	"""
	user = select_user(msg.from_user, msg.chat)
	if user:
		if user.user_name.isspace():
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()

		now_karma = f"Текущая карма для {name}: <b>{user.karma}</b>."
		bot.send_message(msg.chat.id, now_karma, parse_mode="HTML")

	else:
		name = (msg.from_user.user_name or "") + (msg.from_user.user_nick or "")
		reply_text = f"Вас еще не благодарили, {name}."
		bot.reply_to(msg, reply_text)


@bot.message_handler(commands=["topbest"], func=is_my_message)
def top_best(msg):
	"""
	Функция которая выводит список пользователей с найбольшим значением кармы
	"""
	selected_user = KarmaUser.select()\
		.where((KarmaUser.karma > 0) & (KarmaUser.chatid == msg.chat.id))\
		.order_by(KarmaUser.karma.desc())\
		.limit(10)

	top_mess = "Топ благодаримых:\n"
	for i, user in enumerate(selected_user):
		if user.user_name:
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()
		top_mess += f"*{i+1}*. {name}, ({user.karma} раз)\n"
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["topbad"], func=is_my_message)
def top_bad(msg):
	"""
	Функция которая выводит список пользователей с найменьшим значением кармы
	"""
	selected_user = KarmaUser.select() \
		.where((KarmaUser.karma < 0) & (KarmaUser.chatid == msg.chat.id)) \
		.order_by(KarmaUser.karma.asc()) \
		.limit(10)

	top_mess = "Топ ругаемых:\n"
	for i, user in enumerate(selected_user):
		if user.user_name:
			name = user.user_name.strip()
		else:
			name = user.user_nick.strip()
		top_mess += f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	if not selected_user:
		top_mess = "Никто еще не заслужил быть в этом списке."
	bot.send_message(msg.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["freezeme", "unfreezeme"], func=is_my_message)
def freeze_me(msg):
	"""
	Функция, которая используется для заморозки значения кармы.
	Заморозка происходит для пользователя, вызвавшего функцию.
	Заморозка означает отключение возможности смены кармы для пользователя,
	и запрет на смену кармы другим пользователям
	"""
	user = select_user(msg.from_user, msg.chat)
	freeze = True if msg.text[1:9] == "freezeme" else False

	result = ""
	if not user:
		insert_user(msg.from_user, msg.chat)
		user = select_user(msg.from_user, msg.chat)
	if user.is_freezed != freeze:
		result += "Статус изменен. "
		KarmaUser.update(is_freezed=(not user.is_freezed)).where(
			(KarmaUser.userid == msg.from_user.id) &
			(KarmaUser.chatid == msg.chat.id)).execute()
	result += f"Текущий статус: карма {'за' if freeze else 'раз'}морожена."
	bot.reply_to(msg, result)


@bot.message_handler(commands=["gods_intervention"])
def gods_intervention(msg):
	"""
	Небольшая функция, которая позволяет создателю бота 
	добавить кому и сколько угодно очков кармы в обход 
	всех ограничений.
	"""
	if len(msg.text.split()) == 1:
		return

	if msg.from_user.id not in config.gods:
		bot.reply_to(msg, "Ты не имеешь власти.")

	result = int(msg.text.split()[1])
	change_karma(msg.reply_to_message.from_user, msg.chat, result)


@bot.message_handler(commands=["unmute"], func=is_my_message)
def un_mute(msg):
	if msg.from_user.id not in config.gods:
		return
	Limitation.delete().where(
		(Limitation.userid == msg.reply_to_message.from_user.id) &
		(Limitation.chatid == msg.chat.id)).execute()

	bot.send_message(msg.chat.id, "Возможность менять карму возвращена.")


@bot.message_handler(commands=["the_gods_says"])
def the_gods_says(message):
	"""
	Если от лица создателя чата нужно что-то сказать во 
	все чаты, где используется бот.
	TODO
	"""
	if message.from_user.id not in config.gods:
		return


def is_karma_changing(text):
	result = []

	# Проверка изменения кармы по смайликам
	if len(text) == 1:
		if text in config.good_emoji:
			result.append(1)
		if text in config.bad_emoji:
			result.append(-1)
		return result

	# Обработка текста для анализа
	text = text.lower()
	for punc in string.punctuation:
		text = text.replace(punc, "")
	for white in string.whitespace[1:]:
		text = text.replace(white, "")

	# Проверка изменения кармы по тексту сообщения
	for word in config.good_words:
		if word == text \
				or (" "+word+" " in text) \
				or text.startswith(word) \
				or text.endswith(word):
			result.append(1)

	for word in config.bad_words:
		if word in text \
				or (" "+word+" " in text) \
				or text.startswith(word) \
				or text.endswith(word):
			result.append(-1)
	return result


def is_karma_freezed(msg):
	"""
	Функция для проверки индивидуальной блокировки кармы.
	:param msg: Объект собщения, из которого берутся id чата и пользователей
	:return: True если у кого-то из учасников заморожена карма. Иначе False.
	"""

	# Выборка пользователей, связаных с сообщением.
	# Использованы логические операторы поскольку (из документации Peewee):
	# Peewee uses bitwise operators (& and |)
	# rather than logical operators (and and or)
	banned_request = KarmaUser.select().where(
		(KarmaUser.chatid == msg.chat.id) &
		(
			(KarmaUser.userid == msg.from_user.id) |
			(KarmaUser.userid == msg.reply_to_message.from_user.id)
		)
	)

	# У выбраных пользователей проверяется статус заморозки
	for req in banned_request:
		if req.is_freezed:
			name = ""
			if not req.user_name.isspace():
				name = req.user_name.strip()
			else:
				name = req.user_nick.strip()

			# Сообщение, у кого именно заморожена карма
			reply_text = f"Юзер: {name}.\nСтатус кармы: Заморожена."
			bot.send_message(msg.chat.id, reply_text)
			return True
	return False


def is_karma_abuse(msg):
	hours_ago_12 = pw.SQL("current_timestamp-interval'12 hours'")
	limitation_request = Limitation.select().where(
		(Limitation.timer > hours_ago_12) &
		(Limitation.userid == msg.from_user.id) &
		(Limitation.chatid == msg.chat.id))

	if len(limitation_request) > 7:
		timer = limitation_request[0].timer + datetime.timedelta(hours=15)
		reply_text = f"Возможность изменять карму будет доступна с: {timer}"
		bot.send_message(msg.chat.id, reply_text)
		return True
	return False


def reputation(msg, text):
	""" TODO """

	# Если сообщение большое, то прервать выполнение функции
	if len(text) > 100:
		return

	# Если карму не пытаются изменить, то прервать выполнение функции
	how_much_changed = is_karma_changing(text)
	if not how_much_changed:
		return

	# При попытке поднять карму самому себе прервать выполнение функции
	if msg.from_user.id == msg.reply_to_message.from_user.id:
		bot.send_message(msg.chat.id, "Нельзя изменять карму самому себе.")
		return

	# Ограничение на изменение кармы для пользователя во временной промежуток
	if is_karma_abuse(msg):
		return

	if is_karma_freezed(msg):
		return

	bot.send_chat_action(msg.chat.id, "typing")

	# Если значение кармы все же можно изменить: изменяем
	result = sum(how_much_changed)
	if result != 0:
		Limitation.create(
			timer=pw.SQL("current_timestamp"),
			userid=msg.from_user.id,
			chatid=msg.chat.id)
		change_karma(msg.reply_to_message.from_user, msg.chat, result)

	if result > 0:
		res = "повышена"
	elif result < 0:
		res = "понижена"
	else:
		res = "не изменена"

	user = KarmaUser.select().where(
		(KarmaUser.userid == msg.reply_to_message.from_user.id) &
		(KarmaUser.chatid == msg.chat.id)).get()

	if not user.user_name.isspace():
		name = user.user_name.strip()
	else:
		name = user.user_nick.strip()

	now_karma = f"Карма {res}.\nТекущая карма для {name}: <b>{user.karma}</b>."
	bot.send_message(msg.chat.id, now_karma, parse_mode="HTML")


def reply_exist(msg):
	return msg.reply_to_message


@bot.message_handler(content_types=["text"], func=reply_exist)
def changing_karma_text(msg):
	reputation(msg, msg.text)


@bot.message_handler(content_types=["sticker"], func=reply_exist)
def changing_karma_sticker(msg):
	reputation(msg, msg.sticker.emoji)


# bot.polling(none_stop=True)


# Дальнейший код используется для установки и удаления вебхуков
server = Flask(__name__)


@server.route("/bot", methods=['POST'])
def get_message():
	""" TODO """
	decode_json = request.stream.read().decode("utf-8")
	bot.process_new_updates([telebot.types.Update.de_json(decode_json)])
	return "!", 200


@server.route("/")
def webhook_add():
	""" TODO """
	bot.remove_webhook()
	bot.set_webhook(url=config.url)
	return "!", 200


@server.route("/<password>")
def webhook_rem(password):
	""" TODO """
	password_hash = hashlib.md5(bytes(password, encoding="utf-8")).hexdigest()
	if password_hash == "5b4ae01462b2930e129e31636e2fdb68":
		bot.remove_webhook()
		return "Webhook removed", 200
	else:
		return "Invalid password", 200


server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

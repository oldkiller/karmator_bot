#!usr/bin/python3
import hashlib
import string
import os

from flask import Flask, request
import psycopg2 as pg
import telebot

import config


TELEGRAM_API = os.environ["telegram_token"]
DATABASE_ADDRESS = os.environ["DATABASE_URL"]
bot = telebot.TeleBot(TELEGRAM_API)
data = pg.connect(DATABASE_ADDRESS)
data.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
curs = data.cursor()


def isMyMessage(text):
	# В групповых чатах нужно быть уверенным, 
	# что сообщение относится именно к этому боту
	text = text.split()[0]
	text = text.split("@")
	if len(text) > 1:
		if text[1] != config.bot_name:
			return False
	return True


@bot.message_handler(commands=["start"])
def start(message):
	if not isMyMessage(message.text): 
		return
	bot.send_message(message.chat.id, "Здравствуйте, я бот,\
	 который отвечает за подсчет кармы в групповых чатах.")


@bot.message_handler(commands=["help"])
def helps(message):
	if not isMyMessage(message.text): 
		return
	help_mess="Правила работы бота:\
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
	\n/source Ссылка на GitHub репозиторий"
	bot.send_message(message.chat.id, help_mess)


@bot.message_handler(commands=["source"])
def source(message):
	"""
	Функция, которая по запросу возвращает ссылку на гитхаб-репозиторий
	"""
	if not isMyMessage(message.text): 
		return
	bot.send_message(message.chat.id, 
		"Исходный код доступен по ссылке: " + config.source_link)


def select_user(user, chat):
	"""
	Функция для извлечения данных о пользователе \n
	user - пользователь, данные которого необходимы \n
	chat - чат, в котором находится пользователь
	"""
	select_user_str = "select * from karma_user where userid=%s and chatid=%s"
	curs.execute(select_user_str, (user.id, chat.id))
	return curs.fetchone()


def insert_user(user, chat):
	"""
	Функция для добавления нового пользователя \n
	user - данные добавляемого пользователя \n
	chat - чат, в котором находится пользователь
	"""
	first_name = user.first_name if user.first_name else ""
	last_name = user.last_name if user.last_name else ""
	username = user.username if user.username else ""
	curs.execute("insert into karma_user values(%s,%s,%s,%s,%s,%s)", 
		(user.id, chat.id, 0, first_name+" "+last_name, username, False))


def change_karm(user, chat, result):
	"""
	Функция для изменения значения кармы пользователя
	user - пользователь, которому нужно изменить карму \n
	chat - чат, в котором находится пользователь \n
	result - насколько нужно изменить карму
	"""
	selected_user = select_user(user, chat)
	if not selected_user:
		insert_user(user, chat)
	curs.execute("update karma_user set karma=karma+%s where \
		userid=%s and chatid=%s", (result, user.id, chat.id))
	data.commit()


def limitation(user, chat):
	"""
	Функция, которая используется для ограничения видачи кармы
	user - пользователь, который изменял карму \n
	chat - чат, в котором находится пользователь
	"""
	curs.execute("insert into limitation values\
		(%s,%s,current_timestamp+interval'3 hour')",
		(user.id, chat.id))
	data.commit()


@bot.message_handler(commands=["mykarm"])
def mykarm(message):
	"""
	Функция, которая выводит значение кармы для пользователя.
	Выводится карма для пользователя, который вызвал функцию
	"""
	if not isMyMessage(message.text): 
		return
	
	# user[2] - значение кармы, user[3] - имя и фамилия,
	# user[4] - никнейм. 
	user = select_user(message.from_user, message.chat)
	if user:
		name = user[3].strip() if user[3].isspace() else user[4].strip()
		now_karma = f"Текущая карма для {name}: <b>{user[2]}</b>."
		bot.send_message(message.chat.id, now_karma, parse_mode="HTML")
	else:
		bot.reply_to(message, f"Вас еще не благодарили, {name}.")


@bot.message_handler(commands=["topbest"])
def topbest(message):
	"""
	Функция которая выводит список пользователей с найбольшим значением кармы
	"""
	if not isMyMessage(message.text): 
		return
	curs.execute("select * from karma_user where karma>0 and chatid=%s \
		order by karma desc limit 10", (message.chat.id,))
	user = curs.fetchall()
	top_mess = "Топ благодаримых:\n"
	for i in range(len(user)):
		name = user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess += f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["topbad"])
def topbad(message):
	"""
	Функция которая выводит список пользователей с найменьшим значением кармы
	"""
	if not isMyMessage(message.text): return
	curs.execute("select * from karma_user where karma<0 and chatid=%s\
		order by karma limit 10", (message.chat.id,))
	user = curs.fetchall()
	top_mess = "Топ ругаемых:\n"
	for i in range(len(user)):
		name = user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess += f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")


@bot.message_handler(commands=["freezeme","unfreezeme"])
def freezeme(message):
	"""
	Функция, которая используется для заморозки значения кармы.
	Заморозка происходит для пользователя, вызвавшего функцию
	"""
	if not isMyMessage(message.text): return
	user = select_user(message.from_user, message.chat)
	ban = True if message.text[1:9] == "freezeme" else False
	if not user: 
		insert_user(message.from_user, message.chat)
		user = select_user(message.from_user, message.chat)
	if user[5] != ban:
		curs.execute("update karma_user set is_banned=not is_banned where \
			userid=%s and chatid=%s", (message.from_user.id, message.chat.id))
	result = "Статус изменен. " if user[5]!=ban else ""
	result += "Текущий статус: карма "
	result += "заморожена" if ban else "разморожена"
	bot.send_message(message.chat.id, result)


@bot.message_handler(commands=["gods"])
def gods(message):
	"""
	Небольшая функция, которая позволяет создателю бота 
	добавить кому и сколько угодно очков кармы в обход 
	всех ограничений.
	"""
	if message.from_user.id not in config.gods:
		bot.reply_to(message, "You not owner")
	
	if len(message.text.split()) == 1: 
		return
	
	result = int(message.text.split()[1])
	change_karm(message.reply_to_message.from_user, message.chat, result)


@bot.message_handler(commands=["unmute"])
def unmute(message):
	if not isMyMessage(message.text): 
		return
	if message.from_user.id not in config.gods:
		return
	curs.execute("delete from limitation where chatid=%s and userid=%s;", 
		(message.reply_to_message.from_user.id, message.chat.id))
	data.commit()
	bot.send_message(message.chat.id, "Розблокировано")


@bot.message_handler(commands=["the_gods_says"])
def the_gods_says(message):
	"""
	Если от лица создателя чата нужно что-то сказать во 
	все чаты, где используется бот.
	"""
	if message.from_user.id not in config.gods: 
		return

	text = " ".join(message.text.split()[1:])

	select_chat = "select distinct chatid from karma_user"
	curs.execute(select_chat)
	for chat in curs.fetchall():
		bot.send_message(chat, text)


def is_karma_changing(text):
	result = []
	
	if len(text) == 1:
		if text in config.good_emoji:
			result.append(1)
		if text in config.bad_emoji:
			result.append(-1)
		return result

	text = text.lower()
	for punc in string.punctuation:
		text = text.replace(punc, "")
	for white in string.whitespace[1:]:
		text = text.replace(white, "")

	for word in config.good_words:
		if word in text:
			result.append(1)
			break
	for word in config.bad_words:
		if word in text:
			result.append(-1)
			break
	return result

reply_exist = lambda msg: msg.reply_to_message

@bot.message_handler(content_types=["text"], func=reply_exist)
def changing_karma_text(msg):
	reputation(msg, msg.text)


@bot.message_handler(content_types=["sticker"], func=reply_exist)
def changing_karma_sticker(msg):
	reputation(msg, msg.sticker.emoji)


# @bot.message_handler(func=lambda message: message.reply_to_message != None)
def reputation(msg, text):
	"""
	Функция, в которой происходит определение нескольких параметров:
	- Можно ли изменить значение кармы.
	- Кому и кто изменяет карму.
	"""

	# Большие сообщения пропускаются
	if len(text) > 100: return

	result = is_karma_changing(text)
	
	# Если карму не пытаются изменить, то прервать выполнение функции
	if not result: return
	
	bot.send_chat_action(msg.chat.id, "typing")
	# Защита от поднятия кармы самому себе
	if msg.from_user.id == msg.reply_to_message.from_user.id:
		bot.send_message(msg.chat.id, "Нельзя изменять карму самому себе.")
		return

	# Ограничение на изменение кармы для пользователя во временной промежуток 
	curs.execute("select * from limitation where \
		timer>current_timestamp+interval'3 hour'-interval'12 hour' \
		and userid=%s and chatid=%s",
		(msg.from_user.id, msg.chat.id))
	sends = curs.fetchall()
	if len(sends) > 7:
		bot.send_message(msg.chat.id, "Не спамь. " + str(sends[0][2]))
		return

	# Если у кого то из учасников заморожена карма: прервать выполнение функции
	curs.execute("select * from karma_user where chatid=%s and (userid=%s or userid=%s)",
		(msg.chat.id, msg.from_user.id, msg.reply_to_message.from_user.id))
	if True in [i[5] for i in curs.fetchall()]:
		bot.send_message(msg.chat.id, "Статус кармы: Заморожена.")
		return

	# Если значение кармы все же можно изменить: изменяем
	result = sum(result)
	if result != 0:
		limitation(msg.from_user, msg.chat)
		change_karm(msg.reply_to_message.from_user, msg.chat, result)

	if result > 0:
		res = "повышена"
	elif result < 0:
		res = "понижена"
	elif result == 0: 
		res = "не изменена"
	user = select_user(msg.reply_to_message.from_user, msg.chat)
	name = user[3].strip() if not user[3].isspace() else user[4].strip()
	now_karma = f"Текущая карма для {name}: <b>{user[2]}</b>."
	bot.send_message(msg.chat.id, f"Карма {res}.\n" + now_karma, parse_mode="HTML")

#Дальнейший код используется для установки и удаления вебхуков
server = Flask(__name__)

@server.route("/bot", methods=['POST'])
def get_message():
	""" TODO """
	bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
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
	pasw = hashlib.md5(bytes(password, encoding="utf-8")).hexdigest()
	if pasw == "5b4ae01462b2930e129e31636e2fdb68":
		bot.remove_webhook()
		return "Webhook removed", 200
	else:
		return "Invalid password", 200

server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

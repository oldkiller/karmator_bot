from flask import Flask, request
import psycopg2 as pg
import hashlib
import telebot
import os

telegram_api=os.environ["telegram_token"]
db_address=os.environ["DATABASE_URL"]
bot = telebot.TeleBot(telegram_api)
data = pg.connect(db_address)
data.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
curs=data.cursor()

good_action=["спс", "спасибо", "сяп", "благодарю","благодарность", "помог","sps","spasibo","дякую", 
			"бережи тебе боже","благодарочка","спаси тебя бог","сенкс","thank","аригато","респект",
			"грациас","gracias"]
bad_action=["говно", "пидор", "добровская","жопа","дебил","дурак","барбра стрейзанд",
			"идиот","suka","мразь","бакун","юрченко","мирон"]

@bot.message_handler(commands=["start"])
def start(message):
	bot.send_message(message.chat.id, "Здравствуйте, я бот,\
	 который отвечает за подсчет кармы в групповых чатах.")

@bot.message_handler(commands=["help"])
def helps(message):
	help_mess="Текс, бот перешел в бету. Так что:\n\
	1. Бот реагирует на 29 слов.\n\
	2. Карма отдельная для каждого чата\n\
	3. Ограничения на выдачу кармы: 5 раз в час.\n\
	4. Бот научился понимать слова в тексте более полноценно.\n\
	5. Можно ругаться\n\
	Исходный код доступен по ссылке:\
	https://github.com/oldkiller/karmator_bot\n\
	В создании брали участие: kira_nova, YoYoZ, syt0r"
	bot.send_message(message.chat.id, help_mess)

def add_karma(user,user2,chat):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(user.id,chat.id))
	news=curs.fetchall()
	if news:
		curs.execute("update karma_user set karma=karma+1 where userid=%s and chatid=%s",
			(user.id,chat.id))
	else:
		try:
			first_name=user.first_name if user.first_name else ""
			last_name=user.last_name if user.last_name else ""
			username=user.username if user.username else ""
			curs.execute("insert into karma_user values(%s,%s,%s,%s,%s)", 
				(user.id,chat.id,1,first_name+" "+last_name,username))
		except Exception as e:
			print(str(e))
	curs.execute("insert into limitation values(%s,%s,current_timestamp)",
		(user2.id,chat.id))
	data.commit()

def diff_karma(user,user2,chat):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(user.id,chat.id))
	news=curs.fetchall()
	if news:
		curs.execute("update karma_user set karma=karma-1 where userid=%s and chatid=%s",
			(user.id,chat.id))
	else:
		try:
			first_name=user.first_name if user.first_name else ""
			last_name=user.last_name if user.last_name else ""
			username=user.username if user.username else ""
			curs.execute("insert into karma_user values(%s,%s,%s,%s,%s)", 
				(user.id,chat.id,-1,first_name+" "+last_name,username))
		except Exception as e:
			print(str(e))
	curs.execute("insert into limitation values(%s,%s,current_timestamp)",
		(user2.id,chat.id))
	data.commit()

@bot.message_handler(commands=["mykarm"])
def mykarm(message):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(message.from_user.id,message.chat.id))
	user=curs.fetchall()
	if user:
		user=user[0]
		name=user[2].strip() if user[2].strip() else user[3].strip()
		bot.send_message(message.chat.id, f"Текущая карма для {name}: *{user[1]}*.", parse_mode="Markdown")
	else:
		if message.from_user.first_name or message.from_user.last_name:
			name=message.from_user.first_name if message.from_user.first_name else ""
			name+=message.from_user.last_name if message.from_user.last_name else ""
		elif message.from_user.username:
			name=message.from_user.username
		else: name="Анон-юзер"
		bot.send_message(message.chat.id, f"Вас еще не благодарили, {name}.")

@bot.message_handler(commands=["topbest"])
def topbest(message):
	curs.execute("select * from karma_user \
		where karma>0 and chatid=%s \
		order by karma desc limit 10",(message.chat.id,))
	user=curs.fetchall()
	top_mess="Топ благодаримых:\n"
	for i in range(len(user)):
		name=user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess+=f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")

@bot.message_handler(commands=["topbad"])
def topbest(message):
	curs.execute("select * from karma_user \
		where karma<0 and chatid=%s\
		order by karma limit 10", (message.chat.id))
	user=curs.fetchall()
	top_mess="Топ ругаемых:\n"
	for i in range(len(user)):
		name=user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess+=f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True if message.reply_to_message else False)
def reputation(message):
	if message.from_user.id==message.reply_to_message.from_user.id:
		bot.send_message(message.chat.id, "Нельзя добавлять карму самому себе.")
		return
	curs.execute("select * from limitation where \
		timer>current_timestamp-interval'1 hour' \
		and userid=%s and chatid=%s",
		(message.from_user.id,message.chat.id))
	isacc=curs.fetchall()
	print(isacc, len(isacc))
	if len(isacc)>=5:
		bot.send_message(message.chat.id, "Не спамь")
		return
	res=""
	text=message.text.lower()
	for rep in good_action:
		if rep in text:
			add_karma(message.reply_to_message.from_user,
				message.from_user,message.chat)
			res="повышена"
			break
	for rep in bad_action:
		if rep in text:
			diff_karma(message.reply_to_message.from_user,
				message.from_user,message.chat)
			res="понижена"
			break
	if not res: return
	curs.execute("select * from karma_user where userid=%s and chatid=%s", 
		(message.reply_to_message.from_user.id,message.chat.id))
	user=curs.fetchall()
	user=user[0]
	name=user[3].strip() if user[3].strip() else user[4].strip()
	bot.send_message(message.chat.id, f"Карма {res}.\nТекущая карма для {name}: *{user[2]}*.", parse_mode="Markdown")

server = Flask(__name__)

@server.route("/bot", methods=['POST'])
def getMessage():
	bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
	return "!", 200

@server.route("/")
def webhook_add():
	bot.remove_webhook()
	bot.set_webhook(url="https://karmatorbot.herokuapp.com/bot")
	return "!", 200

@server.route("/<password>")
def webhook_del(password):
	pasw=hashlib.md5(bytes(password, encoding="utf-8")).hexdigest()
	if pasw=="5b4ae01462b2930e129e31636e2fdb68":
		bot.remove_webhook()
		return "Webhook removed", 200
	else:
		return "Invalid password", 200

server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
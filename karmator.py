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
			"бережи тебе боже"]
bad_action=["говно", "пидор", "добровская"]

@bot.message_handler(commands=["start"])
def start(message):
	bot.send_message(message.chat.id, "Здравствуйте, я бот,\
	 который отвечает за подсчет кармы в групповых чатах.")

@bot.message_handler(commands=["help"])
def helps(message):
	help_mess="Текс, бот пока в альфе. Так что:\n\
	1. Бот реагирует только на 8 слов, которые обозначают благодарность(2 в транслите)\n\
	2. Карма общая для всех чатов\n\
	3. Ограничений на выдачу кармы нет.\n\
	4. Бот научился понимать слова в тексте более полноценно.\n\
	Исходный код доступен по ссылке:\
	[github](https://github.com/oldkiller/karmator_bot)"
	bot.send_message(message.chat.id, help_mess, parse_mode="Markdown")

def parse_message(text):
	text=text.split()
	res={"num":[],"word":[]}
	if len(text)>40:
		return res
	for i in text:
		if i.isnumeric():
			res["num"].append(float(i))
		else:
			res["word"].append(i)
	return res

def add_karma(user):
	curs.execute("select * from karma_user where ids=%s",(user.id,))
	news=curs.fetchall()
	if news:
		curs.execute("update karma_user set karma=karma+1 where ids=%s",(user.id,))
	else:
		try:
			first_name=user.first_name if user.first_name else ""
			last_name=user.last_name if user.last_name else ""
			username=user.username if user.username else ""
			curs.execute("insert into karma_user values(%s,%s,%s,%s)", 
				(user.id,1,first_name+" "+last_name,username))
		except Exception as e:
			bot.send_message(message.chat.id, str(e))
	data.commit()

def diff_karma(user):
	curs.execute("select * from karma_user where ids=%s",(user.id,))
	news=curs.fetchall()
	if news:
		curs.execute("update karma_user set karma=karma-1 where ids=%s",(user.id,))
	else:
		try:
			first_name=user.first_name if user.first_name else ""
			last_name=user.last_name if user.last_name else ""
			username=user.username if user.username else ""
			curs.execute("insert into karma_user values(%s,%s,%s,%s)", 
				(user.id,-1,first_name+" "+last_name,username))
		except Exception as e:
			bot.send_message(message.chat.id, str(e))
	data.commit()	

@bot.message_handler(commands=["mykarm"])
def mykarm(message):
	curs.execute("select * from karma_user where ids=%s", (message.from_user.id,))
	user=curs.fetchall()
	if user:
		user=user[0]
		name=user[2].strip() if user[2].strip() else user[3].strip()
		bot.send_message(message.chat.id, f"Текущая карма для {name}: *{user[1]}*.", parse_mode="Markdown")
	else:
		if message.from_user.first_name or message.from_user.last_name:
			name=message.from_user.first_name if message.from_user.first_name else ""
			name+=message.from_user.last_name if message.from_user.last_name else ""
			# name=str(message.from_user.first_name) +" "+ str(message.from_user.last_name)
		elif message.from_user.username:
			name=message.from_user.username
		else: name="Анон-юзер"
		bot.send_message(message.chat.id, f"Вас еще не благодарили, {name}.")

@bot.message_handler(commands=["topbest"])
def topbest(message):
	curs.execute("select * from karma_user order by karma desc limit 10")
	user=curs.fetchall()
	top_mess="Топ благодаримых:\n"
	for i in range(len(user)):
		name=user[i][2].strip() if user[i][2].strip() else user[i][3].strip()
		top_mess+=f"*{i+1}*. {name}, ({user[i][1]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True if message.reply_to_message else False)
def reputation(message):
	if message.from_user.id==message.reply_to_message.from_user.id:
		bot.send_message(message.chat.id, "Нельзя добавлять карму самому себе.")
		return
	text=message.text.lower()
	for rep in good_action:
		if rep in text:
			add_karma(message.reply_to_message.from_user)
			res="повышена"
			break
	else: return
	for rep in bad_action:
		if rep in text:
			diff_karma(message.reply_to_message.from_user)
			res="понижена"
			break
	else: return
	curs.execute("select * from karma_user where ids=%s", (message.reply_to_message.from_user.id,))
	user=curs.fetchall()
	user=user[0]
	name=user[2].strip() if user[2].strip() else user[3].strip()
	bot.send_message(message.chat.id, f"Карма {res}.\nТекущая карма для {name}: *{user[1]}*.", parse_mode="Markdown")

# if __name__=="__main__":
# 	bot.polling(none_stop=True)

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
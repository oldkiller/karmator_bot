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
			"грациас","gracias","храни тебя бог"]
bad_action=["говно", "пидор", "добровская","жопа","дебил","дурак","барбра стрейзанд",
			"идиот","suka","сука","мразь","бакун","юрченко","мирон"]

@bot.message_handler(commands=["start"])
def start(message):
	bot.send_message(message.chat.id, "Здравствуйте, я бот,\
	 который отвечает за подсчет кармы в групповых чатах.")

@bot.message_handler(commands=["help"])
def helps(message):
	text=message.text.split("@")
	if len(text)>1:
		if text[1]!="Karmator_bot":
			return
	help_mess="Текс, бот перешел в бету. Так что:\n\
	1. Бот реагирует на 29 слов.\n\
	2. Карма отдельная для каждого чата.\n\
	3. Ограничения на выдачу кармы: 5 раз в час.\n\
	4. Можно заморозить свою карму.\n\
	5. Можно ругаться.\n\
	Исходный код доступен по ссылке:\
	https://github.com/oldkiller/karmator_bot"
	bot.send_message(message.chat.id, help_mess)

def change_karm(user, user2, chat, result):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(user.id, chat.id))
	news=curs.fetchall()
	if news:
		curs.execute("update karma_user set karma=karma+%s where userid=%s and chatid=%s",
			(result, user.id, chat.id))
	else:
		first_name=user.first_name if user.first_name else ""
		last_name=user.last_name if user.last_name else ""
		username=user.username if user.username else ""
		curs.execute("insert into karma_user values(%s,%s,%s,%s,%s,%s)", 
			(user.id, chat.id, result, first_name+" "+last_name, username, False))
	curs.execute("insert into limitation values(%s,%s,current_timestamp)",
		(user2.id, chat.id))
	data.commit()

@bot.message_handler(commands=["mykarm"])
def mykarm(message):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(message.from_user.id,message.chat.id))
	user=curs.fetchone()
	if user:
		print(user)
		name=user[3].strip() if user[3].isspace() else user[4].strip()
		bot.send_message(message.chat.id, f"Текущая карма для {name}: <b>{user[2]}</b>.", parse_mode="HTML")
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
	curs.execute("select * from karma_user where karma>0 and chatid=%s \
		order by karma desc limit 10", (message.chat.id,))
	user=curs.fetchall()
	top_mess="Топ благодаримых:\n"
	for i in range(len(user)):
		name=user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess+=f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")

@bot.message_handler(commands=["topbad"])
def topbad(message):
	curs.execute("select * from karma_user where karma<0 and chatid=%s\
		order by karma limit 10", (message.chat.id,))
	user=curs.fetchall()
	top_mess="Топ ругаемых:\n"
	for i in range(len(user)):
		name=user[i][3].strip() if user[i][3].strip() else user[i][4].strip()
		top_mess+=f"*{i+1}*. {name}, ({user[i][2]} раз)\n"
	bot.send_message(message.chat.id, top_mess, parse_mode="Markdown")

@bot.message_handler(commands=["freezeme","unfreezeme"])
def cleanseme(message):
	curs.execute("select * from karma_user where userid=%s and chatid=%s",
		(message.from_user.id,message.chat.id))
	user=curs.fetchone()
	ban=True if message.text[1:9]=="freezeme" else False
	if not user:
		first_name=message.from_user.first_name if message.from_user.first_name else ""
		last_name=message.from_user.last_name if message.from_user.last_name else ""
		username=message.from_user.username if message.from_user.username else ""
		curs.execute("insert into karma_user values(%s,%s,%s,%s,%s,%s)", 
			(message.from_user.id,message.chat.id, 0, first_name+" "+last_name, username, ban))
	elif user[5]==False and ban==True:
		curs.execute("update karma_user set is_banned=True where userid=%s and chatid=%s",
			(message.from_user.id, message.chat.id))
	elif user[5]==True and ban==False:
		curs.execute("update karma_user set is_banned=False where userid=%s and chatid=%s",
			(message.from_user.id, message.chat.id))
	if not user:
		result="Статус изменен. "
	else:
		result="" if user[5]==ban else "Статус изменен. "
	result+="Текущий статус: карма "
	result+="заморожена" if ban else "разморожена"
	bot.send_message(message.chat.id, result)

@bot.message_handler(commands=["the_gods_are_always_right"])
def gods(message):
	if message.from_user.id!=212668916: return
	if len(message.text.split())==1: return
	result=int(message.text.split()[1])
	change_karm(message.reply_to_message.from_user, message.from_user, message.chat, result)

@bot.message_handler(func=lambda message: True if message.reply_to_message else False)
def reputation(message):
	if len(message.text)>150: return
	result=[]
	text=message.text.lower()
	for rep in good_action:
		if rep in text:
			result.append(1)
			break
	for rep in bad_action:
		if rep in text:
			result.append(-1)
			break
	if not result: return
	if message.from_user.id==message.reply_to_message.from_user.id:
		bot.send_message(message.chat.id, "Нельзя добавлять карму самому себе.")
		return
	curs.execute("select * from limitation where \
		timer>current_timestamp-interval'1 hour' \
		and userid=%s and chatid=%s",
		(message.from_user.id, message.chat.id))
	sends=curs.fetchall()
	if len(sends)>5:
		bot.send_message(message.chat.id, "Не спамь")
		return
	curs.execute("select * from karma_user where chatid=%s and (userid=%s or userid=%s)",
		(message.chat.id,message.from_user.id,message.reply_to_message.from_user.id))
	if True in [i[5] for i in curs.fetchall()]:
		bot.send_message(message.chat.id, "Статус кармы: Заморожена.")
		return
	result=sum(result)
	if result!=0:
		change_karm(message.reply_to_message.from_user, message.from_user, message.chat, result)
	if result>0:  res="повышена"
	if result<0:  res="понижена"
	if result==0: res="не изменена"
	curs.execute("select * from karma_user where userid=%s and chatid=%s", 
		(message.reply_to_message.from_user.id, message.chat.id))
	user=curs.fetchone()
	name=user[3].strip() if not user[3].isspace() else user[4].strip()
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
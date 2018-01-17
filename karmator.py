from flask import Flask, request
import psycopg2 as pg
import hashlib
import telebot
import os

tele_api=os.environ["telegram_token"]
db_address=os.environ["DATABASE_URL"]
bot = telebot.TeleBot("497913397:AAF1PnbwocP97InvSKLzsyvi0QLA7brW1-c")
data = pg.connect(db_address)
data.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

@bot.message_handler(commands=["start"])
def start(message):
	bot.send_message(message.chat.id, "Дратути")

@bot.message_handler(commands=["help"])
def helps(message):
	help_mess="Все ключи начинаются с минуса (-)\n"\
	"Ключи для рассписания: {d - day, t - tomorrow, w - week, f - full}"
	bot.send_message(message.chat.id, help_mess)

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

@bot.message_handler(func=lambda message: True if message.reply_to_message else False)
def reputation(message):
	print("im reputation")
	print(message)
	text=parse_message(message.text)
	if "спс" in text["word"]:
		bot.send_message(message.chat.id, "Карма принята")
		data.execute("update karma_user set karma=karma+1 where ids=%s",(212668916,))
	# print(message.reply_to_message.from_user.username)
	# print(message.reply_to_message.from_user)
	bot.send_message(message.chat.id, "++")

# @bot.message_handler(content_types=['text'])
# def another_text(message):
# 	print(message)

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
		return "Invalid password"

server.run(host="0.0.0.0", port=os.environ.get('PORT', 5000))
import os

import peewee as pw

# Магия монтажа. Peewee не умеет (26.06.2019) принимать в себя адрес базы одной
# строкой, так что приходится парсить вручную.
DATABASE_ADDRESS = os.environ["DATABASE_URL"]

# DATABASE_ADDRESS.replace("postgres://", "")
#
# splitters = [":", "@", ":", "/", " "]
# database_data = []
# for split in splitters:
# 	database_data.append(DATABASE_ADDRESS.split(split, maxsplit=1)[0])
# 	DATABASE_ADDRESS.replace(database_data[-1] + split, "")
#
# user, password, host, port, database_name = database_data
#
#
# db = pw.PostgresqlDatabase(database_name,
# 	user=user,
# 	host=host,
# 	password=password,
# 	port=port)


db = pw.PostgresqlDatabase(DATABASE_ADDRESS, autocommit=True)


class BaseModel(pw.Model):

	class Meta:
		database = db


class KarmaUser(BaseModel):
	userid = pw.IntegerField(null=False)
	chatid = pw.IntegerField(null=False)
	karma = pw.IntegerField(null=False)
	user_name = pw.CharField(max_length=100, null=False)
	user_nick = pw.CharField(max_length=50, null=False)
	is_freezed = pw.BooleanField(column_name="is_banned")

	class Meta:
		db_table = "karma_user"
		primary_key = pw.CompositeKey("userid", "chatid")


class Limitation(BaseModel):
	userid = pw.IntegerField(null=False)
	chatid = pw.IntegerField(null=False)
	timer = pw.TimestampField(null=False, primary_key=True)

	class Meta:
		db_table = "limitation"




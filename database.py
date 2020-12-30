import os

import peewee as pw
from playhouse.db_url import connect

from logger import db_log


DB_ADDRESS = os.environ["DATABASE_URL"]
db = connect(DB_ADDRESS)

db_log.debug(f"Create database with address {DB_ADDRESS}")

# В запросах в програме использованы логические
# операторы поскольку (из документации Peewee):
# Peewee uses bitwise operators (& and |)
# rather than logical operators (and and or)

# Postgres database -+


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




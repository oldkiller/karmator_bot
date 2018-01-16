import psycopg2 as pg

class Postgress():
	def __init__(self,address):
		self.db=pg.connect(address)
		self.db.set_isolation_level(pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
		self.cur=self.db.cursor()

	def __del__(self):
		self.cur.close()
		self.db.close()

	def write(self,user,col,data):
		self.cur.execute(f"""select {col} from users where ids = {user}""")
		if self.cur.fetchall():
			self.cur.execute(f"""update users set {col}='{data}' where ids = {user}""")
			self.db.commit()
		else:
			self.cur.execute(f"""insert into users (ids,{col}) values({user},'{data}')""")
			self.db.commit()

	def read(self,user,col):
		self.cur.execute(f"""select {col} from users where ids={user}""")
		data=self.cur.fetchall()[0][0]
		print(data)
		if data:
			if type(data)==type("str"):
				data=data.strip()
			return data
		else:
			return None

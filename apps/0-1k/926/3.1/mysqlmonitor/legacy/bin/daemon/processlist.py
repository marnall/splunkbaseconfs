import MySQLdb
from collector import Collector

class ProcessList(Collector):

	def sourcetype(self):
		return 'mysql-processlist'

	def isMultivalue(self):
		return True

	def collect(self, conn):
		xstr = lambda s: str(s) or "" # Convert None to empty string
		vals = list()
		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT USER, HOST, DB, COMMAND, TIME, STATE FROM INFORMATION_SCHEMA.PROCESSLIST")
		rows = cursor.fetchall()
		for row in rows:
			val = [xstr(row["USER"]), xstr(row["HOST"]), xstr(row["DB"]), xstr(row["COMMAND"]), xstr(row["TIME"]), xstr(row["STATE"])]
			vals.append(val)
		cursor.close()

		return vals

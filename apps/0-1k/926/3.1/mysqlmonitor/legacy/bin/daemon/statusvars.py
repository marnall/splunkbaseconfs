import MySQLdb
from collector import Collector

class StatusVars(Collector):

	def sourcetype(self):
		return 'mysql-statusvars'

	def isMultivalue(self):
		return False

	def collect(self, conn):
		vals = dict()	
		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT VARIABLE_NAME, VARIABLE_VALUE FROM INFORMATION_SCHEMA.GLOBAL_STATUS")
		rows = cursor.fetchall()
		for row in rows:
			vals[row["VARIABLE_NAME"]] = row["VARIABLE_VALUE"]
		cursor.execute("SELECT VARIABLE_NAME, VARIABLE_VALUE FROM INFORMATION_SCHEMA.GLOBAL_VARIABLES")
		for row in rows:
			vals[row["VARIABLE_NAME"]] = row["VARIABLE_VALUE"]
		cursor.close()

		return vals

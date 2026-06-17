import MySQLdb
from collector import Collector

class SlaveStatus(Collector):

	def sourcetype(self):
		return 'mysql-slavestatus'

	def isMultivalue(self):
		return False

	def collect(self, conn):
		vals = dict()	
		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SHOW SLAVE STATUS")
		rows = cursor.fetchall()
		for row in rows:
			vals["Slave_IO_Running"] = row["Slave_IO_Running"]
			vals["Slave_SQL_Running"] = row["Slave_SQL_Running"]
			vals["Last_IO_Errno"] = row["Last_IO_Errno"]
			vals["Last_IO_Error"] = row["Last_IO_Error"]
			vals["Last_SQL_Errno"] = row["Last_SQL_Errno"]
			vals["Last_SQL_Error"] = row["Last_SQL_Error"]
			vals["Seconds_Behind_Master"] = row["Seconds_Behind_Master"]
		cursor.close()

		return vals

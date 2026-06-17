import MySQLdb
from collector import Collector

class TableStats(Collector):

	def sourcetype(self):
		return 'mysql-tablestats'

	def isMultivalue(self):
		return True

	def collect(self, conn):
		xstr = lambda s: str(s) or "" # Convert None to empty string
		vals = list()	
		cursor = conn.cursor(MySQLdb.cursors.DictCursor)
		cursor.execute("SELECT t.TABLE_SCHEMA, t.TABLE_NAME, t.DATA_LENGTH, t.INDEX_LENGTH, t.DATA_FREE, t.AUTO_INCREMENT, " +
			"c.DATA_TYPE, c.COLUMN_TYPE, c.NUMERIC_PRECISION, c.NUMERIC_SCALE " +
			"FROM INFORMATION_SCHEMA.TABLES t " +
			"LEFT JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME AND " +
				"t.TABLE_SCHEMA = c.TABLE_SCHEMA AND " +
				"c.COLUMN_KEY = 'PRI' AND " +
				"c.EXTRA = 'auto_increment' " +
				"WHERE t.TABLE_SCHEMA NOT IN ('mysql', 'information_schema')")
		rows = cursor.fetchall()
		for row in rows:
			val = [xstr(row["TABLE_SCHEMA"]),
				xstr(row["TABLE_NAME"]),
				xstr(row["DATA_LENGTH"]),
				xstr(row["INDEX_LENGTH"]),
				xstr(row["DATA_FREE"]),
				xstr(row["AUTO_INCREMENT"]),
				xstr(row["DATA_TYPE"]),
				xstr(row["COLUMN_TYPE"]),
				xstr(row["NUMERIC_PRECISION"]),
				xstr(row["NUMERIC_SCALE"])]
			vals.append(val)
		cursor.close()

		return vals

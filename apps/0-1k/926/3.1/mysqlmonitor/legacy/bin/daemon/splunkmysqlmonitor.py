#!/usr/bin/env python

import sys, time, os, socket
import ConfigParser
import MySQLdb
from daemon import Daemon
from datetime import datetime
from statusvars import StatusVars
from processlist import ProcessList
from slavestatus import SlaveStatus
from tablestats import TableStats

class SplunkMySQLMonitor(Daemon):
	
	def run(self):
		try:
			path = os.path.dirname(os.path.realpath(__file__))
			config = ConfigParser.ConfigParser()
			config.read([path + '/config.ini'])

			self.mysql_host = config.get('mysql', 'host')
			self.mysql_port = config.getint('mysql', 'port')
			self.mysql_username = config.get('mysql', 'username')
			self.mysql_password = config.get('mysql', 'password')

			self.splunk_host = config.get('splunk', 'host')
			self.splunk_port = config.getint('splunk', 'port')

			self.statusvars_interval = config.getint('statusvars', 'interval')
			self.processlist_interval = config.getint('processlist', 'interval')
			self.slavestatus_interval = config.getint('slavestatus', 'interval')
			self.tablestats_interval = config.getint('tablestats', 'interval')

		except:
			print "Config file not found or malformed"
			sys.exit(1)

		try:
			self.conn = MySQLdb.connect(
				host = self.mysql_host,
				port = self.mysql_port,
				user = self.mysql_username,
				passwd = self.mysql_password)
		except MySQLdb.Error, err:
			print "Could not connect to database: Error %d: %s" % (err.args[0], err.args[1])
			sys.exit(1)

		self.collectors = [
			StatusVars(self.statusvars_interval),
			ProcessList(self.processlist_interval),
			SlaveStatus(self.slavestatus_interval),
			TableStats(self.tablestats_interval)
		]

		while True:
			time.sleep(1)
			current = datetime.now()
			for c in self.collectors:
				vals = c.update(self.conn, current)
				if vals != None:
					s = ["***SPLUNK*** host=",
							self.mysql_host,
							" source=mysql sourcetype=",
							c.sourcetype(),
							"\n"]
					if c.isMultivalue():
						for k in vals:
							s.append("\t".join(k))
							s.append("\n")
					else:
						s.append("[" + current.isoformat() + "] ")
						for k in vals:
							s.append("%s=%s," % (k, vals[k]))				

					try:
						client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
						client.connect((self.splunk_host, self.splunk_port))
						client.send(''.join(s))
						client.close()
					except:
						print "Failed to connect to Splunk TCP socket"	

if __name__ == "__main__":
	daemon = SplunkMySQLMonitor(os.path.dirname(os.path.realpath(__file__)) + '/splunkmysql.pid')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print "Unknown command. Usage: %s <start|stop|restart>" % sys.argv[0]
			sys.exit(2)
		sys.exit(0)
	else:
			print "Usage: %s <start|stop|restart>" % sys.argv[0]
			sys.exit(2)

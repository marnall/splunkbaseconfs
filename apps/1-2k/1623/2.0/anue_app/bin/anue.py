from ConfigParser import ConfigParser
import json
import httplib2
import logging, logging.handlers
import pprint
import os, sys
import time
import datetime
import threading
import random 

#----------------------------------------------------------------------
# Import additional scripts
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
APP_BIN_DIR = os.path.join(SPLUNK_HOME,'etc','apps','anue_app','bin')

for filename in os.listdir(APP_BIN_DIR):
    if filename.endswith(".py"):
        fPath = os.path.join(APP_BIN_DIR,filename)
        sys.path.append(fPath)

import AnueConfigParser


#----------------------------------------------------------------------	
PROTOCOL = "https://"
STATISTICS = "/api/stats"
JSON_STATS_OBJ_NAME = "stats_snapshot"
JSON_CHASSIS_KEY = "chassis"

TP_CURRENT_UTILIZATION_STAT = "tp_current_tx_utilization"
NP_CURRENT_UTILIZATION_STAT = "np_current_rx_utilization"
TP_CURRENT_PASS_STAT = "tp_current_pass_percent_packets"


#----------------------------------------------------------------------	
class Collector(threading.Thread):
	myName = None
	anueChassis = None
	http = None
	statistics_url = None
	logger = None
	
	
	def __init__(self, name, anueCh):
		threading.Thread.__init__(self)
		self.myName = name
		self.anueChassis = anueCh
		self.http = httplib2.Http(disable_ssl_certificate_validation=True)
		self.http.add_credentials(self.anueChassis.getUsername(), self.anueChassis.getPassword())
		
		self.setLogger()
		self.logger.info("init collector : "+str(self.myName))
		self.prepare()
		
		
	def prepare(self):
		self.logger.info("--> enter prepare()")
		self.statistics_url = PROTOCOL+self.anueChassis.getHost()+":"+self.anueChassis.getWebApiPort()+STATISTICS
		self.logger.info("statistics url: "+self.statistics_url)
		self.logger.info("<-- exit prepare()")
		
	def run(self):
		if(self.anueChassis.needsToPoll()):
			self.pollAnue()
			
			
	def setLogger(self):
		log_file_name = "Anue-"+self.myName+".log"
		log_file = os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk',log_file_name)

		self.logger = logging.getLogger(log_file_name)
		self.logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
		self.logger.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		fileHandler = logging.handlers.RotatingFileHandler(log_file, maxBytes=25000000, backupCount=5)
		formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
		fileHandler.setFormatter(formatter)
		self.logger.addHandler(fileHandler)

			
	def pollAnue(self):
		self.logger.info("--> enter pollAnue()")
		try:
			responseStats = self.getStatistics()
			self.logger.info("get statistics completed with status code : "+str(responseStats.status))

			if (responseStats.status != 200):
				self.logger.info("could not obtain anue statistics")				
			
		except Exception as e:
			self.logger.exception("Exception polling chassis for statistics")

		self.logger.info("<-- exit pollAnue()")
		
	def getStatistics(self):
		self.logger.info("--> enter getStatistics()")
		
		resp, content = self.http.request(self.statistics_url,
			method='POST',
			headers={'Content-Type': 'application/json', 'charset':'UTF-8','Connection':'close','Host':self.anueChassis.getHost()},
			body=self.anueChassis.getJsonBodyQuery())

		# index data into splunk 
		if resp.status == 200:
			self.printResponseToSplunk(content)
	
		self.logger.info("  response header")
		self.logger.info(pprint.pformat(resp))
		self.logger.info("<-- exit getStatistics()")
		
		return resp
		
		# move percent	from interval 0 - 1 to 0 - 100		
	def scalePercent(self, value):
		self.logger.info("--> enter scalePercent()")

		toRet = value
		try:
			fPercent = float(value)		
			fPercent = fPercent * 100
			iPercent = int(fPercent)
			toRet = iPercent
		except Exception as ex:
			self.logger.exception("Could not scale correctly percent statistic")
		
		self.logger.info("<-- exit scalePercent()")
		return toRet
		
		
	def processJsonStatisticsObject(self, json):
		self.logger.info("--> enter processJsonStatisticsObject()")
		
		#handle current percent utilization percent for tool ports
		tp_utilization_stat = json.get(TP_CURRENT_UTILIZATION_STAT)
		if(tp_utilization_stat != None):
			tp_utilization_stat = self.scalePercent(tp_utilization_stat)
			json[TP_CURRENT_UTILIZATION_STAT] = tp_utilization_stat
				
		#handle current pass packets percent for tool ports 
		current_pass_stat = json.get(TP_CURRENT_PASS_STAT)
		if(current_pass_stat != None):
			current_pass_stat = self.scalePercent(current_pass_stat)
			json[TP_CURRENT_PASS_STAT] = current_pass_stat
			
		#handle current percent utilization percent for network ports	
		np_utilization_stat = json.get(NP_CURRENT_UTILIZATION_STAT)
		if(np_utilization_stat != None):
			np_utilization_stat = self.scalePercent(np_utilization_stat)
			json[NP_CURRENT_UTILIZATION_STAT] = np_utilization_stat
			
		self.logger.info("<-- exit processJsonStatisticsObject()")
	
		
		
	def printResponseToSplunk(self,s):
		self.logger.info("--> enter printResponseToSplunk()")
		try:
			jdata = json.loads(s)
			stats = jdata[JSON_STATS_OBJ_NAME]	
			for st in stats:			
			    # Augment json  object with additional information
				st[JSON_CHASSIS_KEY]=self.anueChassis.getHost()
				# Move usefull percent statistcs from domain 0-1 into domain 0-100
				self.processJsonStatisticsObject(st)			
                # Index each json statistics object to Splunk
				print (json.dumps(st))
				sys.stdout.flush()
				
		except Exception as e:
			self.logger.exception("Exception while indexing data into Splunk")
		
		self.logger.info("<-- exit printResponseToSplunk()")
		

#----------------------------------------------------------------------	
if __name__ == '__main__':	

	chList = AnueConfigParser.readAnueChassisData()
	
	for ch in chList:
		try:
			coll = Collector(ch.getHost(), ch)
			coll.start()
		except Exception as e:
			pass
	

	

# Splunk to InfluxDB module
# Yash Ravala 01/30/2015
# 09/29/2016 Updated for strings in values
# 09/29/2017 Updated for https support

import os, logging
from logging.handlers import TimedRotatingFileHandler
splkhome = os.environ['SPLUNK_HOME']
splvar = os.path.join(splkhome, 'var', 'log', 'splunk', 'influxdbmod.log')


### Set Logging
log = logging.getLogger('splunk_to_influxdb')
log.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler = logging.handlers.TimedRotatingFileHandler(splvar,when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
log.addHandler(handler)

try:
	log.debug('Importing libs')
	import sys, subprocess, re, string, urllib2, json, gzip, csv, requests
	import splunklib.results as results
	import splunklib.client as client
	from datetime import datetime
	from subprocess import Popen, PIPE
	from urlparse import urlparse
	log.debug('Importing libs successful')
except Exception, e:
	log.error('Unable to import libs %s' % str(e))
	sys.exit()


def get_influxdb_conf(splk_srchname):
        try:
                influxdblist = splk_srchname.split('__')
                global infdb_instance, infdb_measurement
                infdb_instance = influxdblist[2]
                infdb_measurement = influxdblist[1]
                log.info('Received SearchName %s, Processed %s and %s' % (splk_srchname,infdb_instance,infdb_measurement))
	except Exception, e:
                log.error('Problem extracting influxdb conf from srchname %s -- %s' % (splk_srchname, str(e)))
                sys.exit()

def splunk_connect(skey):
        try:
                global service
                splkapp = "influxdb_connect"
                service = client.connect(token = skey, app = splkapp)
                log.info('Successfully connected to splunk with token')
        except Exception, e:
                log.error('Unable to connect to splunk %s' % str(e))
                sys.exit()

def get_influxdb_instance_details():
        try:
                req = service.request("storage/collections/data/influxdbconf/%s" % infdb_instance,method='get')
                log.info('Successfully accessed collection data for %s' % infdb_instance)
        except Exception, e:
                log.error('Unable to access collection data  %s' % str(e))
                sys.exit()

        try:
		global infdbhost, infdbport, infdbuser, infdbaccs, infdbdb, posturl
                coldata_raw = req.body.read()
                coldata = re.sub(r'[([\])\']','', coldata_raw)
                coldata_port = json.loads(coldata)
                infdbhost = (coldata_port['infdbHost'])
                infdbport = (coldata_port['infdbPort'])
                infdbuser = (coldata_port['infdbUser'])
                infdbaccs = (coldata_port['_infdbPass'])
                infdbdb = (coldata_port['infdbDatabase'])
                
                if infdbport.startswith('http'):
			infdbpandp = infdbport.split(':')
			global infdb_protocol, infdb_port
			infdb_protocol = infdbpandp[0]
			infdb_port = infdbpandp[1]
			log.info('Port Protocol received %s,%s' % (infdb_protocol,infdb_port))
		else:
			infdb_protocol = "unset"
									
		if infdb_protocol == "https":
			posturl = 'https://%s:%s/write?db=%s&precision=ms&p=%s&u=%s' % (infdbhost,infdb_port,infdbdb,infdbaccs,infdbuser)
		else:
                	posturl = 'http://%s:%s/write?db=%s&precision=ms&p=%s&u=%s' % (infdbhost,infdbport,infdbdb,infdbaccs,infdbuser)
                	
                log.info('Successfully parsed collection data %s,%s,%s,%s' % (infdbhost,infdbport,infdbuser,infdbdb))
        except Exception, e:
                log.error('Unable to parse collection data %s' % str(e))
                sys.exit()


def process_splk_results(splk_results):
        try:
                rslts = gzip.open(splk_results, 'rb')
                log.info('Successfully opened results at %s' % splk_results)
        except Exception, e:
                log.error('Unable to open results %s' % str(e))
                sys.exit()

        try:
		rsltsdata = csv.DictReader(rslts, delimiter=',')		
	
                for rslt in rsltsdata:	
			## Create the InfluxDB JSON reults se
			infrslt = {}
			infrslt['measurement'] = infdb_measurement
 			infrslt['tags'] = {}
			infrslt['fields'] = {}
			for field in rslt.keys():
				if field.startswith('__mv_'):
					del rslt[field]
			for field in rslt.keys():
                                if field.startswith('ts_'):
                                        infrslt['time'] = rslt[field]
				elif field.startswith('val_'):
					inffield = re.sub(r'val_','',field,1)
					if len(rslt[field]) == 0:
						rsltvval = 0
						infrslt['fields'][inffield] = rsltvval
	
					else:
						infrslt['fields'][inffield] = rslt[field]
	
                                elif field.startswith('valst_'):
                                        inffield = re.sub(r'valst_','',field,1)
                                        infrslt['fields'][inffield] = "\"%s\"" % rslt[field]
	
				else:
					infrslt['tags'][field] = rslt[field]
			
			try:
				stringtags=str(infrslt['tags'])
				rawtags=re.sub('[{}\']','', stringtags)
				tagformat1=re.sub(': ','=', rawtags)
				tagformat2=re.sub(', ',',', tagformat1)
				tagstrip=tagformat2.strip()
				tags=re.sub(' ','\ ', tagstrip)
				log.debug('tagname received -%s-' % tags)
				stringfields=str(infrslt['fields'])
				rawfields=re.sub('[{}\']','', stringfields)
				fieldformat1=re.sub(': ','=', rawfields)
				fieldformat2=re.sub(', ',',', fieldformat1)
				fields=fieldformat2.strip()
#				fields=re.sub(':','=', rawfields)
				inputdata='%s,%s %s %s' % (infrslt['measurement'],tags,fields,infrslt['time'])
				log.debug('Successfully created dump for resultset %s. Attempting influxDB write ' % inputdata)
				res = requests.post('%s' % posturl,data='%s' % inputdata,headers={'Content-Type': 'application/octet-stream'})
			except Exception, e:
	        	        log.error('Unable to write %s to InfluxDB %s' % (infrslt,str(e)))
	       	        	sys.exit()

                log.info('Successfully read contents at %s, Data Exported to InflxDB Instance %s' % (splk_results,infdb_instance))
        except Exception, e:
                log.error('Unable to export data to InfluxDB %s' % str(e))
                sys.exit()


# Port data from Splunk to InfluxDB
# Triggered via a scheduled search
# Yash Ravala 01/30/2015

import os, sys, json
splkhome=os.environ['SPLUNK_HOME']
applib=os.path.join(splkhome, 'etc', 'apps', 'influxdb_connect', 'lib')
sys.path.append("%s" % applib)


# Splunk InfluxDB Module
from splunk_to_influxdb import *

if len(sys.argv) > 1 and sys.argv[1] == "--execute":
	# read the payload from stdin as a json string
	payload = json.loads(sys.stdin.read())
	# extract the file path and alert config from the payload
	configuration = payload.get('configuration')
else:
	log.error('FATAL Unsupported execution mode expected --execute flag')
	sys.exit()




try:
        log.info('Script influxdbcustomalert.py initiated' )
	#skey_raw = sys.stdin.readline().strip()
	skey = payload.get('session_key')
	#skey = urllib2.unquote(skey_urlc).decode('utf8')
	splk_results = payload.get('results_file')
	splk_srchname = payload.get('search_name')
        log.info('Successfully received inputs from Splunk %s and %s' % (splk_srchname,splk_results))
except Exception, e:
        log.error('Unable to open results %s' % str(e))
        sys.exit()


try:
        log.info('Running get_influxdb_conf for %s' % splk_srchname)
	get_influxdb_conf(splk_srchname)
	log.info('Completed get_influxdb_conf for %s' % splk_srchname)
except Exception, e:
        log.error('Unable to run get_influxdb_conf %s' % str(e))
        sys.exit()

try:
        log.info('Running splunk_connect with raw token %s' % skey)
        splunk_connect(skey)
	log.info('Completed splunk_connect with raw token %s' % skey)
except Exception, e:
        log.error('Unable to run splunk_connect %s' % str(e))
        sys.exit()

try:
        log.info('Running get_influxdb_instance_details')
        get_influxdb_instance_details()
	log.info('Completed get_influxdb_instance_details')
except Exception, e:
        log.error('Unable to run get_influxdb_instance_details %s' % str(e))
        sys.exit()

try:
        log.info('Running process_splk_results for %s' % splk_results)
        process_splk_results(splk_results)
	log.info('Completed process_splk_results for %s' % splk_results)
except Exception, e:
        log.error('Unable to run process_splk_results for %s %s' % (splk_results,str(e)))
        sys.exit()

import os,re,sys,time, splunk.Intersplunk
#import logging as logger

import yammercommon

import splunk.mining.dcutils as dcu
import splunk.Intersplunk as isp

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#dynamically load in any eggs in /etc/apps/snmp_ta/bin
EGG_DIR = SPLUNK_HOME + "/etc/apps/yammer_ta/bin/"
os.environ['REQUESTS_CA_BUNDLE'] = EGG_DIR + '/cacert.pem'

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(EGG_DIR + filename) 
       
import yampy

def yamuser():
	try:

#		logger = dcu.getLogger()
#		logger.info("Starting the yamuser command")

		# Get configuration values from jira.conf
		splunk_conf = yammercommon.getSplunkConf()
		
#		logger.root.setLevel(logging.DEBUG)

		local_conf = yammercommon.getLocalConf()

		access_token = local_conf.get('yammercommon', 'access_token')

#		logger.debug("Access Token %s" % access_token)

		yammer = yampy.Yammer(access_token=access_token)

		results, dummyresults, settings = isp.getOrganizedResults()

		keywords, options = isp.getKeywordsAndOptions()

		output_field = options.get('out', 'yammer_user_full_name')
		user_id_fld = options.get('field', 'sender_id')

		#userid = argvals.get("id")

		if results:
			for result in results:
				userid = result[user_id_fld]
				if userid:
					#user = yammer.users.find(userid)
					result[str(output_field)] = "test"
					#user.full_name
		else:
			result={}
			#user = yammer.users.find(userid)
			#result[str(user_name)] = user.full_name
			#results.append(result)

		splunk.Intersplunk.outputResults(results)

	except Exception, e:
		import traceback
		stack =  traceback.format_exc()
		splunk.Intersplunk.generateErrorResults(str(e))
#		logger.error(str(e) + ". Traceback: " + str(stack))

if __name__ == '__main__':
	yamuser()
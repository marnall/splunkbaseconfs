import re,sys,time,math, splunk.Intersplunk
from base64 import b64encode, b64decode

import sys, os
import logging, logging.handlers
import splunk

def setup_logging():
    logger = logging.getLogger('splunk.kom_app_base64')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "kom_splunk_base64.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

def dobase64(results, settings):

	try:
		fields, argvals = splunk.Intersplunk.getKeywordsAndOptions()
		actionstr        = argvals.get("action", "decode")

		if actionstr == "encode":
			meth=b64encode
		if actionstr == "decode":
			meth=b64decode


		for r in results:
			for f in fields:
				if f in r:
					try:
						message = r[f]
						#message might require padding to be valid base64 string to decode
						if actionstr == "decode":
							message = message.ljust((int)(math.ceil(len(message) / 4)) * 4, '=')
						base64_bytes = message.encode('ascii')
						message_bytes = meth(base64_bytes)
						r[f] = message_bytes.decode('ascii')
					except (TypeError, UnicodeEncodeError, UnicodeDecodeError) as err:
						#Ignore encoding exceptions and return orginal value rather have the SPL command fail
						logger.warn("Field: %s failed base64 Action: %s  Reason: " + str(err), message, actionstr)
						continue

		splunk.Intersplunk.outputResults(results)
	except:
		import traceback
		stack =  traceback.format_exc()
		results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

        
logger = setup_logging()
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
results = dobase64(results, settings)


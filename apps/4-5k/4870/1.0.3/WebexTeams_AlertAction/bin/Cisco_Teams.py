###Cisco Teams###########################################
# # version 1.0
import json
import logging, logging.handlers
from optparse import OptionParser
import sys, os
import ConfigParser
from collections import OrderedDict
import csv
import time
import requests

import httplib, urllib
import base64
import string

#import requests

dir = os.path.join(os.path.join(os.environ.get('SPLUNK_HOME')), 'etc', 'apps', 'WebexTeams_AlertAction', 'bin', 'lib')
if not dir in sys.path:
  sys.path.append(dir)

from CsvResultParser import *
from urlparse import urlparse
from requests_toolbelt.multipart.encoder import MultipartEncoder

def getResults(results_file):
  parser = CsvResultParser(results_file)
  results = parser.getResults()
  return results

def setup_logging():
    logger = logging.getLogger('splunk.teams')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "teams.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'WebexTeams_AlertAction')
    directory = os.path.join(SPLUNK_HOME, BASE_LOG_PATH)
    if not os.path.exists(directory):
        os.makedirs(directory)

    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=10024000, backupCount=100)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    LOGGING_File = os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME)
    return logger

def setupSplunkLogger(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose=True):
    '''
    Takes the base logging.logger instance, and scaffolds the splunk logging namespace
    and sets up the logging levels as defined in the config files
    '''

    levels = getSplunkLoggingConfig(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose)

    for item in levels:
        loggerName = item[0]
        level = item[1]
        logging.getLogger(loggerName).setLevel(getattr(logging, level))


def getSplunkLoggingConfig(baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose):

    loggingLevels = []

    # read in config file and set logging levels
    if os.access(localConfigFile, os.R_OK):
        if verbose:
            baseLogger.info('Using local logging config file: %s' % localConfigFile)
        logConfig = open(localConfigFile, 'r')
    else:
        if verbose:
            baseLogger.info('Using default logging config file: %s' % defaultConfigFile)
        logConfig = open(defaultConfigFile, 'r')

    try:
        inStanza = False
        for line in logConfig:

            # strip comments
            line = line.strip()
            if '#' in line:
                line = line[:(line.index('#'))]

            # skip blank lines
            line = line.strip()
            if not line:
                continue

            # # # skip malformatted lines: stanza, key=value
            if line.startswith('['):
                if not line.endswith(']') or line.index(']') != (len(line) - 1):
                    continue
            elif '=' in line:
                key_test, value_test = line.split('=')
                if not key_test or not value_test:
                    continue
            else:
                continue

            # # # validation done, now we finally have parsing logic proper
            if not inStanza and line.startswith('[%s]' % loggingStanzaName):
                inStanza = True
                continue
            elif inStanza:
                if line.startswith('['):
                    break
                else:
                    name, level = line.split('=', 1)
                    if verbose:
                        baseLogger.info('Setting logger=%s level=%s' % (name.strip(), level.strip()))
                    loggingLevels.append((name.strip(), level.strip().upper()))
    except Exception, e:
        baseLogger.exception(e)
    finally:
        if logConfig:
            logConfig.close()

    return loggingLevels

def to_string(s):
    try:
        return str(s)
    except:
        #Change the encoding type if needed
        return s.encode('utf-8')

def reduce_item(key, value):
    global reduced_item

    #Reduction Condition 1
    if type(value) is list:
        i=0
        for sub_item in value:
            reduce_item(key+'_'+to_string(i), sub_item)
            i=i+1

    #Reduction Condition 2
    elif type(value) is dict:
        sub_keys = value.keys()
        for sub_key in sub_keys:
            reduce_item(key+'_'+to_string(sub_key), value[sub_key])

    #Base Condition
    else:
        reduced_item[to_string(key)] = to_string(value)

def execute(resturl, resdata, bearer, roomId, include_result, attach_csv, teamscert=None):

    resdata['roomId'] = roomId
    link = """<p><a href="%s">URL</a></p>""" % settings.get ('results_link', ['null']).encode ('UTF8','replace')

    result=json.dumps(settings.get('results'))

    data = "**Search Name : **" + settings.get ('search_name', ['null']) + "\n\n**Search Link: **" + link + "\n\n**Severity: **" + settings.get ('configuration').get ('Severity', ['null']) +"\n\n**Search ID : **"+ settings.get('sid')+"\n\n**App : **"+ settings.get('app')

    if int(include_result):
        data = data + "\n\n**Result : **" + result

    resdata['markdown'] = data
    resjs = json.dumps (resdata)
    logger.info ("Sending the following event data to Teams REST Server: \n" + resjs)
    url = resturl
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': 'Bearer ' + bearer}

    if url.lower().startswith("https://"):
        try:
            '''
            In case of HTTPS, SSL certificate is mandatory.
            '''
            if teamscert:
                res = requests.post(url,  data=resjs, headers=headers, verify=teamscert, timeout=60)
                logger.info("Successfully sent the event data to Teams Room")
                logger.info("Response received from Teams REST Server: " + str(res))
            else:
                res = requests.post(url,  data=resjs, headers=headers, verify=False, timeout=60)
                logger.info("Successfully sent the event data to Teams Room w/o SSL")
                logger.info("Response received from Teams Room: " + str(res))
                if int(attach_csv):
                    logger.info("include attachement: " + attach_csv)
                    dt = int(time.time())
                    fileName = 'results.'+str(dt)+'.csv.gz'
                    m = MultipartEncoder({'roomId': roomId,
                                          'text': 'Attachment for '+settings.get('sid'),
                                          'files': (fileName, open(settings.get('results_file'), 'rb'),
                                          'text/plain')})
                    headers = {'Content-Type': m.content_type, 'Accept':'application/json', 'Authorization':'Bearer '+bearer}
                    attachRes = requests.post(url,  data=m, headers=headers, verify=False, timeout=60)
                    logger.info("Response received for attachment: "+str(attachRes))
        except Exception as exception:
            exceptionMsg = str(exception)
            valueTeamssert = ""
            if "unknown error" in exceptionMsg:
                exceptionMsg = "SSL certificate verification failed"
                if teamscert:
                    valueteamsert = teamscert

            logger.error("Failed to send the event data to Teams REST Server : " + exceptionMsg + " : " + valueteamsert)
            raise Exception("An error has occurred while executing HTTPS POST request with Teams REST Server with error message: " + exceptionMsg + " : " + valueteamsert)
    elif url.lower().startswith("http://"):
        try:
            SPLUNK_HOME = os.environ['SPLUNK_HOME']
            configfile = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'TA-Cisco-Teams', 'default', 'teams.conf')
            config = ConfigParser.RawConfigParser()
            config.read(configfile)
            enforcevalue = config.get('https', 'enforce_https')
            if enforcevalue.lower() == 'true':
                logger.error("HTTP support is disabled for the app TA-Cisco-Teams")
            elif enforcevalue.lower() == 'false':
                headers = {'Content-Type': 'application/json', 'Accept':'application/json', 'Authorization':'Bearer '+bearer}
                logger.info (headers)
                res = requests.post(url, data=resjs, headers=headers, timeout=60)
                logger.info("Successfully send the event data to Teams REST Server")
                logger.info("Response received from Teams REST Server: " + str(res))


            else:
                logger.error("Configured value of enforce_https in inputs.confi is invalid :" + enforcevalue)

        except Exception as exception:
            exceptionMsg = str(exception)
            logger.error("Failed to send the event data to Teams REST Server : " + exceptionMsg)
            raise Exception("An error has occurred while executing HTTP POST request with Teams REST Server with error message: " + exceptionMsg)
    else:
            logger.error("Configured URL is not valid : " + url)



if __name__ == '__main__':

    logger = setup_logging()
    logger.info("##################################")
    logger.info("Teams Alert Script Execution Started")
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.info >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    try:
       settings = json.loads(sys.stdin.read())
       config = settings['configuration']
       del settings['result']
       # Get results from results.csv.gz file
       results = getResults(settings.get('results_file'))
       # Adding results dict to payload
       settings.update({"results": results})

       resturl = config['url']
       bearer = config['bearer']
       roomId = config['roomId']
       include_result = config['include_result']
       attach_csv = config['attach_csv']

       if resturl.lower().startswith("https://"):
            try:
                teamscert = config['teamscertificate']
                execute(resturl, settings, teamscert, bearer, roomId, include_result,attach_csv);
            except:
                execute(resturl, settings, bearer, roomId, include_result,attach_csv);
            else:
                execute(resturl, settings, bearer, roomId,include_result,attach_csv);

       logger.info("Teams Alert Script Execution completed successfully")

    except Exception, e:
       logger.error("Teams Alert Script Execution Failed: " + str(e))
       sys.exit(3)

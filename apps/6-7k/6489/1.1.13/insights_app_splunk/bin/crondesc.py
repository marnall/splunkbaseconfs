#!/usr/bin/env python
import csv
import socket
import requests
import uuid
import sys 
if sys.version_info >= (3, 0):
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
    import time, os, re, json, urllib.request, urllib.parse, urllib.error, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si
else:
    from urllib2 import urlopen, Request, HTTPError, URLError
    import sys, time, os, re, json, urllib, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si

from cron_descriptor import ExpressionDescriptor, Options, DescriptionTypeEnum, CasingTypeEnum, Exception

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "cron_desc.log"



def setup_logging():  # setup logging
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')
    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', LOG_FILE_NAME), mode='a', maxBytes=1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    logger.propagate = False
    return logger

def die(msg):
    logger.error(msg)
    exit(msg)


@Configuration()
class CronDesc(StreamingCommand):

    def stream(self, events):
        options = Options()
        options.verbose = True
        options.throw_exception_on_parse_error = True
        options.casing_type = CasingTypeEnum.Sentence
        
        for event in events:
            if 'cron_expression' in event :
                cron_expression = event["cron_expression"]
                descripter = ExpressionDescriptor(cron_expression, options)
                try:
                    readable = str(descripter.get_description(DescriptionTypeEnum.FULL))
                except Exception.FormatException as e:
                    readable = str(e)
                
                event["cron_human_readable"] = str(readable)
            yield event

dispatch(CronDesc, sys.argv, sys.stdin, sys.stdout, __name__)


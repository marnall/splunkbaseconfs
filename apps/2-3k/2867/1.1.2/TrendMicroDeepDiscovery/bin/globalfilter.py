#!/usr/bin python

import csv
import sys
import splunk.Intersplunk
import hashlib
from sets import Set
import string
import os
import time
import re
import logging
from libs.Global_conf import Global_conf

logging.basicConfig(filename='globalfilter.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

def init_hash(conf_val,hash_obj):
	conf_val = conf_val.split(",")
	conf_dict = {}
	for h in conf_val:
		hash_obj[h] = 0

me = os.path.dirname(os.path.realpath(__file__))
logger.debug(os.path.join(me, "..", "django", "TrendMicroDeepDiscovery", "xml_conf", "global_conf.xml" ))
filter_conf = Global_conf(os.path.join(me, "..", "django", "TrendMicroDeepDiscovery", "xml_conf", "global_conf.xml" ))
appGroup = filter_conf.get_val('protocols')
ruleid = filter_conf.get_val('ruleids')
appGroup_dict,ruleid_dict = {},{}
if appGroup is not None:
	init_hash(appGroup,appGroup_dict)
logger.debug(appGroup_dict.keys())
if ruleid is not None:
	init_hash(ruleid,ruleid_dict)
logger.debug(ruleid_dict.keys())


try:
	keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
	settings = {}
	input_data = splunk.Intersplunk.readResults(sys.stdin, settings)
        fieldnames = set()
        output = []
        for result in input_data:
            if result.get('appGroup') in appGroup_dict:
                continue
            elif result.get('ruleId') in ruleid_dict:
                continue
            else:
                output.append(result)
        
        splunk.Intersplunk.outputResults(output)
except Exception as e:
	splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(str(e) + ": " + traceback.format_exc()))
	logger.error(str(e) + ": " + traceback.format_exc())

import csv
import sys
import splunk.Intersplunk as si
import hashlib
from sets import Set
import string
import os
import time
import re
import logging
from libs.Local_conf import Local_conf

import logging as logger
from logging import handlers

import logging.config
logging.config.fileConfig(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "default", "log.ini"))
logger = logging.getLogger('deepdiscovery')

def init_hash(conf_val):
        conf_val = conf_val.split(",")
        hash_obj = {}
        for h in conf_val:
                hash_obj[h] = 0
        return hash_obj

def localFilter(input_data, settings):
        try:
                keywords, argvals = si.getKeywordsAndOptions()
                me = os.path.dirname(os.path.realpath(__file__))

                filter_conf = Local_conf(os.path.join(me, "..", "django", "TrendMicroDeepDiscovery", "xml_conf", "local_conf.xml" ), *tuple(keywords))
                field_dicts = {}
                for i in keywords:
                        field = filter_conf.get_val(i)
                        field_dict = init_hash(field) if field is not None else {}
                        logger.info(field_dict)
                        field_dicts.update({i:field_dict})


                settings = {}
                output = []
                for result in input_data:
                        match = 0
                        for i in keywords:
                                if result[i] in field_dicts[i].keys():
                                        match = 1
                                        break
                        if match == 0:
                                output.append(result)

        except Exception as e:
                import traceback
                stack =  traceback.format_exc()
                results = si.generateErrorResults(str(e) + ". Traceback: " + str(stack))
                logger.error(str(e) + ". Traceback: " + str(stack))
        return output


if __name__ == '__main__':
    results, dummyresults, settings = si.getOrganizedResults()
    filter_results = localFilter(results, settings)
    si.outputResults(filter_results)

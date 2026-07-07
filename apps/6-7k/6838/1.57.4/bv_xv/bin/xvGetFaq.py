#
# Copyright (c) 2023 BlueVoyant Inc. All Rights Reserved. 
# Reproduction or unauthorized use is prohibited. 
# Unauthorized use is illegal. Violators will be prosecuted. 
# This software contains proprietary trade and business secrets.
#
from __future__ import print_function
from splunk.clilib import cli_common as cli

import fnmatch
import os
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom import minidom
import json
#from xml.dom.minidom import parseString
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    view = ''

    try:


        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('view='):
                    eqsign = arg.find('=')
                    view = arg[eqsign+1:len(arg)]
                    logger.info("xvGetFaq - view: " + view)
        else:
            raise Exception('xvGetFaq-F-001: Usage: xvGetFaq view=<string>')

        print ("Question,Answer,Panel")

        count = 1

        try: 
            cfg = cli.getConfStanza('xv_faqs',view)
            while (count != -1):
                question = cfg.get('question-'+str(count))
                answer = cfg.get('answer-'+str(count))
                panel = cfg.get('panel-'+str(count))
                if question is None:
                    count = -1
                else:
                    if panel is None:
                        panel = ''
                    print (question + "," + answer + "," + panel)
                    count = count + 1
        except: 
            noop = ''

    except Exception as e:
        si.generateErrorResults(e)


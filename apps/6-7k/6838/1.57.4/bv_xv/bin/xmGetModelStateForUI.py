# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os
import platform
import time
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
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    model = ''
    app = ''
    group = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        settings = saUtils.getSettings(sys.stdin)

        print ('app,description,build_status,build_date,build_message,build_actions,build_landscapes,build_graphs,information_density,active_status,activate_date,activate_message,history_startdate, history_enddate')
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmGetModelStateForUI-F-001: Usage: xmGetModelStateForUI model=<string> app=<string>')

        if model == '':
            raise Exception("xmGetModelStateForUI-F-002: parameter 'model' not found")
        if app == '':
            raise Exception("xmGetModelStateForUI-F-003: parameter 'app' not found")

        sessionKey = settings['sessionKey']

        # Get property for model.directory
        modelDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelDir = modelDir.replace("$(SPLUNK_HOME)",splunkHome)

        theFile=modelDir + "/" + model + "/model_state.csv"
        f_obj = open(theFile, rmode)
        reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
        for row in reader:
            print (row[0] + "," + row[1] + "," + row[2] + "," + row[3] + "," + row[4] + "," + row[5] + "," + row[6] + "," + row[7] + "," + row[8] + "," + row[9] + "," + row[10] + "," + row[11] + "," + row[12] + "," + row[13])

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

        logger.info("xmGetModelStateForUI - app: " + app + " model: " + model)
    except Exception as e:
        si.generateErrorResults(e)


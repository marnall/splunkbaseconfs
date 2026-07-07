# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os, platform, time
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom import minidom
import json
#from xml.dom.minidom import parseString
import splunk.rest
import logging
import logging.handlers
from io import open
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)


if __name__ == '__main__':
    model = ''
    app = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        settings = saUtils.getSettings(sys.stdin)

        print ('name,status,model,description,created_date,last_updated,acquire,threshold,sequence,actor,actor_day_of_week,p2p,rule,relevancy,transaction,hazard,threat,rule_package,relevancy_graph,transaction_object,event_range,actor_actorid,actor_interval,actor_day,actor_hour,actor_day_of_month,actor_day_of_week_actorid,actor_day_of_week_interval,actor_day_of_week_day,actor_day_of_week_hour,actor_day_of_week_day_of_month,p2p_interval,p2p_day,p2p_hour,p2p_day_of_month,p2p_category,p2p_businessunit,p2p_managedby,p2p_title,p2p_tag,p2p_region,p2p_gender,p2p_actor_type,activate_date,activate_message')
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmListAnalysisConfigurations-F-001: Usage: xmListAnalysisConfigurations app=<string>')

        if app == '':
            raise Exception("xmListAnalysisConfigurations-F-003: parameter 'app' not found")

        sessionKey = settings['sessionKey']

        # Get property for model.directory
        modelsDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelsDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelsDir = modelsDir.replace("$(SPLUNK_HOME)",splunkHome)

        if (os.path.exists(modelsDir)):
            for modelDir in os.listdir(modelsDir):
                theModelDir = modelsDir + "/" +  modelDir;
                if (os.path.isdir(theModelDir)):
                    for file in os.listdir(theModelDir):
                        if fnmatch.fnmatch(file, 'analysis_*_configuration.csv'):
                            theFile = modelsDir + "/" + modelDir + "/" + file
                            f_obj = open(theFile, rmode)
                            reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
                            for row in reader:
                                print (row[0] + "," + row[1] + "," + row[2] + "," + row[3] + "," + row[4] + "," + row[5] + "," + row[6] + "," + row[7] + "," + row[8] + "," + row[9] + "," + row[10] + "," + row[11] + "," + row[12] + "," + row[13] + "," + row[14] + "," + row[15] + "," + row[16] + "," + row[17] + "," + row[18] + "," + row[19] + "," + row[20] + "," + row[21] + "," + row[22] + "," + row[23] + "," + row[24] + "," + row[25] + "," + row[26] + "," + row[27] + "," + row[28] + "," + row[29] + "," + row[30] + "," + row[31] + "," + row[32] + "," + row[33] + "," + row[34] + "," + row[35] + "," + row[36] + "," + row[37] + "," + row[38] + "," + row[39] + "," + row[40] + "," + row[41] + "," + row[42] + "," + row[43] + "," + row[44])

    except Exception as e:
        si.generateErrorResults(e)

    if platform.system() == 'Windows':
        sys.stdout.flush()
        time.sleep(1.0)

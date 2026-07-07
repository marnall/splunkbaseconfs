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
from xml.dom.minidom import parseString
import splunk.rest
import splunk.rest
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    app = ''
    model = ''
    analysis = ''
    name_list = ''
    type_list = ''
    search_list = ''
    range_list = ''
    status_list = ''
    selected_list = ''
    cron_list = ''
    lastrun_list = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        if len(sys.argv) >4:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('analysis='):
                    eqsign = arg.find('=')
                    analysis = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('name_list='):
                    eqsign = arg.find('=')
                    name_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('type_list='):
                    eqsign = arg.find('=')
                    type_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('search_list='):
                    eqsign = arg.find('=')
                    search_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('range_list='):
                    eqsign = arg.find('=')
                    range_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('status_list='):
                    eqsign = arg.find('=')
                    status_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('selected_list'):
                    eqsign = arg.find('=')
                    selected_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('cron_list'):
                    eqsign = arg.find('=')
                    cron_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('lastrun_list'):
                    eqsign = arg.find('=')
                    lastrun_list = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSaveSearch-F-001: Usage: xmSetSavedSearches app=<string> model=<string> analysis=<string> name_list<string> type_list=<string> search_list=<string> range_list=<string> selected_list=<string> cron_list=<string> lastrun_list=<string>')

        if app == '':
            raise Exception("xmSaveSearch-F-002: parameter 'app' not found")
        elif model == '':
            raise Exception("xmSaveSearch-F-003: parameter 'model' not found")
        elif analysis == '':
            raise Exception("xmSaveSearch-F-003: parameter 'analysis' not found")
        elif name_list == '':
            raise Exception("xmSaveSearch-F-003: parameter 'name_list' not found")
        elif type_list == '':
            raise Exception("xmSaveSearch-F-007: parameter 'type_list' not found")
        elif search_list == '':
            raise Exception("xmSaveSearch-F-007: parameter 'search_list' not found")
        elif range_list == '':
            raise Exception("xmSaveSearch-F-007: parameter 'range_list' not found")
        elif selected_list == '':
            raise Exception("xmSaveSearch-F-007: parameter 'selected_list' not found")
        #elif status_list == '':
        #    raise Exception("xmSaveSearch-F-007: parameter 'status_list' not found")
        #elif cron_list == '':
        #    raise Exception("xmSaveSearch-F-007: parameter 'cron_list' not found")
        #elif lastrun_list == '':
        #    raise Exception("xmSaveSearch-F-007: parameter 'lastrun_list' not found")

        nameArray = name_list.split(",");
        typeArray = type_list.split(",");
        searchArray = search_list.split(",");
        rangeArray = range_list.split(",");
        statusArray = status_list.split(",");
        selectedArray = selected_list.split(",");
        cronArray = cron_list.split(",");
        lastrunArray = lastrun_list.split(",");

        # Get property for model.directory
        modelDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelDir = modelDir.replace("$(SPLUNK_HOME)",splunkHome)
        tmpAnalysis = analysis.replace(" ","_");
        theFile=modelDir + "/" + model + "/" + "analysis_" + tmpAnalysis + "_saved_searches.csv"

        data= []
        i = 0
        for name in nameArray:
            data.append([name,typeArray[i],searchArray[i],rangeArray[i],statusArray[i],selectedArray[i],cronArray[i],lastrunArray[i]])
            i = i + 1

        import csv
        with open(theFile, wmode) as fp:
            a = csv.writer(fp, delimiter=',', quoting=csv.QUOTE_NONE, quotechar='')
            a.writerows(data)

        logger.info("xmSetSavedSearches - Successfully Saved Search Configuration File")
        print ("Response")
        print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

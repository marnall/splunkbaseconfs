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
    model = ''
    app = ''
    name_list =''
    datamodel_list =''
    datamodelobject_list =''
    field_list =''
    search_list=''
    events_list= ''
    actions_list= ''
    dropped_list= ''
    exceptions_list= ''
    status_list = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"
    try:

        if len(sys.argv) > 9:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('name_list='):
                    eqsign = arg.find('=')
                    name_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('datamodel_list='):
                    eqsign = arg.find('=')
                    datamodel_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('datamodelobject_list='):
                    eqsign = arg.find('=')
                    datamodelobject_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('field_list='):
                    eqsign = arg.find('=')
                    field_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('search_list='):
                    eqsign = arg.find('=')
                    search_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('events_list='):
                    eqsign = arg.find('=')
                    events_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actions_list='):
                    eqsign = arg.find('=')
                    actions_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('dropped_list='):
                    eqsign = arg.find('=')
                    dropped_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('exceptions_list='):
                    eqsign = arg.find('=')
                    exceptions_list = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('status_list'):
                    eqsign = arg.find('=')
                    status_list = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSetModelDictionaries-F-001: Usage: xmSetModelDictionaries model=<string> app=<string> name_list=<string> datamodel_list=<string> datamodelobject_list=<string> field_list=<string> search_list=<string> events_list=<string> actions_list=<string> dropped_list=<string> exceptions_list=<string> status_list=<string>')

        if model == '':
            raise Exception("xmSetModelDictionaries-F-002: parameter 'model' not found")
        elif app == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'app' not found")
        elif name_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'name_list' not found")
        elif datamodel_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'datamodel_list' not found")
        #
        #elif datamodelobject_list == '':
        #    raise Exception("xmSetModelDictionaries-F-003: parameter 'datamodelobject_list' not found")
        elif field_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'field_list' not found")
        elif search_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'search_list' not found")
        elif events_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'events_list' not found")
        elif actions_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'actions_list' not found")
        elif dropped_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'dropped_list' not found")
        elif exceptions_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'exceptions_list' not found")
        elif status_list == '':
            raise Exception("xmSetModelDictionaries-F-003: parameter 'status_list' not found")

        names = name_list.split(",")
        datamodels = datamodel_list.split(",")
        datamodelobjects = datamodelobject_list.split(",")
        fields = field_list.split(",")
        searches = search_list.split(",")
        events = events_list.split(",")
        actions = actions_list.split(",")
        dropped = dropped_list.split(",")
        exceptions = exceptions_list.split(",")
        status = status_list.split(",")

        data= []
        i = 0
        for n in names:
            data.append([n,datamodels[i],datamodelobjects[i],fields[i], searches[i],events[i],actions[i],dropped[i],exceptions[i],status[i]])
            i = i + 1

        # Get property for model.directory
        modelDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelDir = modelDir.replace("$(SPLUNK_HOME)",splunkHome)
        modelDir = os.path.normpath (modelDir + "/" + model);
        theFile=os.path.normpath (modelDir + "/model_dictionaries.csv")

        if os.path.exists (modelDir) == False:
            logger.info ("xmSetModelDictionaries - Creating model directory: " + modelDir);
            os.makedirs (modelDir)
        else:
            logger.info ("xmSetModelDictionaries - Model directory: " + modelDir + " exists.");

        import csv
        with open(theFile, rmode) as fp:
            a = csv.writer(fp, delimiter=',')
            a.writerows(data)

        logger.info("xmSetModelDictionaries - Successfully Saved Model Data Dictionary Configuration")
        print ("Response")
        print ("SUCCESS")

    except Exception as e:
        si.generateErrorResults(e)

    if platform.system() == 'Windows':
        sys.stdout.flush()
        time.sleep(1.0)

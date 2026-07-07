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
    description =''
    build_date =''
    build_message = ''
    build_actions = ''
    build_landscapes = ''
    build_graphs = ''
    information_density = ''
    active_date = ''
    active_message = ''
    history_startdate= ''
    history_enddate= ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        if len(sys.argv) >8:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('description='):
                    eqsign = arg.find('=')
                    description = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_status='):
                    eqsign = arg.find('=')
                    build_status = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_date='):
                    eqsign = arg.find('=')
                    build_date = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_message='):
                    eqsign = arg.find('=')
                    build_message = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_actions='):
                    eqsign = arg.find('=')
                    build_actions = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_landscapes='):
                    eqsign = arg.find('=')
                    build_landscapes = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('build_graphs='):
                    eqsign = arg.find('=')
                    build_graphs = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('information_density='):
                    eqsign = arg.find('=')
                    information_density = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('active_status='):
                    eqsign = arg.find('=')
                    active_status = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('active_date='):
                    eqsign = arg.find('=')
                    active_date = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('active_message='):
                    eqsign = arg.find('=')
                    active_message = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('history_startdate='):
                    eqsign = arg.find('=')
                    history_startdate = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('history_enddate='):
                    eqsign = arg.find('=')
                    history_enddate = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSetModelStateForUI-F-001: Usage: xmSetModelStateForUI model=<string> app=<string> description=<string> build_status=<string> build_date=<string> build_message=<string> build_actions=<string> build_landscapes=<string> build_graphs=<string> information_density=<string> active_status=<string> active_date=<string> active_message=<string> history_startdate=<string> history_enddate=<string>')

        if model == '':
            raise Exception("xmSetModelStateForUI-F-002: parameter 'model' not found")
        elif app == '':
            raise Exception("xmSetModelStateForUI-F-003: parameter 'app' not found")

        if active_status is None:
            active_status = ''
        if active_date is None:
            active_date = ''
        if active_message is None:
            active_message = ''
        if build_actions is None:
            build_actions = ''
        if build_landscapes is None:
            build_landscapes = ''
        if build_graphs is None:
            build_graphs = ''
        if information_density is None:
            information_density = ''
        if build_status is None:
            build_status = ''
        if build_date is None:
            build_date = ''

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
        theFile=os.path.normpath (modelDir + "/model_state.csv")

        if os.path.exists (modelDir) == False:
            logger.info ("xmSetModelStateForUI - Creating model directory: " + modelDir);
            os.makedirs (modelDir)
        else:
            logger.info ("xmSetModelStateForUI - Model directory: " + modelDir + " exists.");

        import csv
        with open(theFile, wmode) as fp:
            a = csv.writer(fp, delimiter=',')
            data = [[app,description,build_status,build_date,build_message,build_actions,build_landscapes,build_graphs,information_density,active_status,active_date,active_message,history_startdate,history_enddate]]
            a.writerows(data)

        logger.info("xmSetModelStateForUI - Sucessfully Saved Model State Configuration File")
        print ("Response")
        print ("SUCCESS")

    except Exception as e:
        si.generateErrorResults(e)

    if platform.system() == 'Windows':
        sys.stdout.flush()
        time.sleep(1.0)

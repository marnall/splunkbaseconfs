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
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    app = ''
    analysis = ''
    tmpAnalysis = ''
    model = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        settings = saUtils.getSettings(sys.stdin)

        print ('Response')
        if len(sys.argv) >3:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('analysis='):
                    eqsign = arg.find('=')
                    analysis = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmDeleteAnalysisConfiguration-F-001: Usage: xmDeleteAnalysisConfiguration analysis=<string> model=<string> app=<string>')

        authString = settings['authString'];
        p = re.compile('<username>(.*)\<\/username>')
        user= p.search(authString).group(1)

        # Retrieve list of saved searches and delete them

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
        savedSearchesFile=modelDir + "/" + model + "/analysis_"+tmpAnalysis+"_saved_searches.csv"
        if (os.path.exists(savedSearchesFile)):
            logger.info("xmDeleteAnalysisConfiguration - Reading File: " + savedSearchesFile)
            f_obj = open(savedSearchesFile, rmode)
            reader = csv.reader(f_obj, quoting=csv.QUOTE_NONE);
            for row in reader:
                logger.info("xmDeleteAnalysisConfiguration - Reading Row: " + row[0] + "," + row[4])
                searchName = row[0]
                searchStatus = row[4]
                searchSelected = row[5]
                if searchStatus == 'DONE' or searchStatus == 'ALREADY EXISTS':
                    try:
                        endpoint = '/servicesNS/nobody/'+app+'/saved/searches/' + searchName
                        response, content = splunk.rest.simpleRequest(endpoint, method='DELETE', sessionKey=settings['sessionKey'], raiseAllErrors=False)
                        logger.info("xmDeleteAnalysisConfiguration - Success Removing Saved Search: " + searchName)
                    except Exception as e:
                        logger.info("xmDeleteAnalysisConfiguration - Failure Removing Saved Search: " + searchName)
                        
            f_obj.close();

            # Delete the saved search file
            os.remove(savedSearchesFile);

        # Delete the configuration file
        configurationFile = modelDir + "/" + model + "/analysis_"+tmpAnalysis+"_configuration.csv"
        os.remove(configurationFile);
        logger.info("xmDeleteAnalysisConfiguration - Deleted Analysis Configuration: " + tmpAnalysis)
        print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os
import time
import platform
import re
import csv
import sys
import saUtils
import shutil
from tempfile import NamedTemporaryFile
import splunk.Intersplunk as si
from xml.dom import minidom
import json
import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':

    try:

        splunkHome=os.environ.get('SPLUNK_HOME')
        print ("modelName, createDate")
        count = 0
        theDir = splunkHome + "/etc/apps/bv_xr/scm/backups"
        if (os.path.exists(theDir)):
            for file in os.listdir(theDir):
                theFile = file;
                count = count + 1
                fileDateTime = ''
                path_to_file = theDir + "/" + file
                fileDateTime = time.strftime('%m/%d/%Y %H:%M:%S %Z', time.gmtime(os.path.getmtime(path_to_file)))

                print (theFile + "," + fileDateTime)

        logger.info("xmListExports - Found " + str(count) + " export files");

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)


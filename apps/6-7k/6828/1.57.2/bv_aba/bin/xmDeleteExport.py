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
import shutil
from tempfile import NamedTemporaryFile
from xml.dom import minidom
import json
import splunk.rest
import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

splunkHome=os.environ.get('SPLUNK_HOME')

if __name__ == '__main__':

    theFile = ''

    try:
        print ("Result")
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                theFile = arg;
        else:
            raise Exception('xmDeleteExport-F-001: Usage: xmDeleteExport fileName')

        theDir = splunkHome + "/etc/apps/bv_aba/scm/backups"
        theFile = theDir + "/" + theFile
        logger.info("xmDeleteExport - Delete File: " + theFile)
        if (os.path.exists(theFile)):
            os.remove(theFile);
            print ("File removed")

        print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        print ("FAILURE")


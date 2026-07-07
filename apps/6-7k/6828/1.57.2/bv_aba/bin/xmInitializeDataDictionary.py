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
import shutil
import splunk.Intersplunk as si
from xml.dom.minidom import parseString

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

splunkHome=os.environ.get('SPLUNK_HOME')

if __name__ == '__main__':

    try:
        srcFile  = splunkHome + '/etc/apps/bv_aba/config/data-dictionary-default.json'
        destFile = splunkHome + '/etc/apps/bv_aba/config/data-dictionary.json'
        shutil.copyfile(srcFile,destFile)

        print ("Status")
        print (destFile)

        logger.info("xmInitializeDataDictionary - created: " + destFile)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

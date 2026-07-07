# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os
import platform
import time
import csv
import re
import sys
import saUtils
import splunk.Intersplunk as si
import splunk.rest
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    category = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "ab"
    if python3:
        rmode = "r"
        wmode = "a"

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                category = arg
        else:
            raise Exception('xmAddCategory-F-001: Usage: xmAddCategory category')


        print ('Result')
        splunkHome=os.environ.get('SPLUNK_HOME')
        categoryFilename = splunkHome + "/etc/apps/bv_aba/lookups/categories.csv"

        c = csv.writer(open(categoryFilename, wmode))
        c.writerow([category])
        logger.info("xmAddCategory - Successfully Added Category: " + category)
        print ("Success")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

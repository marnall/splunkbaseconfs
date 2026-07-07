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
from tempfile import NamedTemporaryFile
import splunk.Intersplunk as si
from xml.dom import minidom
import json
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
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                category = arg
        else:
            raise Exception('xmDeleteCategory-F-001: Usage: xmDeleteCategory category')

        print ('Result')
        splunkHome=os.environ.get('SPLUNK_HOME')
        categoryFilename = splunkHome + '/etc/apps/bv_xv/lookups/categories.csv'
        tmpFilename = splunkHome + '/etc/apps/bv_xv/lookups/tmp.csv'

        found = 'false';
        with open(categoryFilename, rmode) as csvfile:
            reader = csv.reader(csvfile)
            c = csv.writer(open(tmpFilename, wmode))
            for row in reader:
                if category == row[0]:
                    found = 'true'
                else:
                    c.writerow(row)

        shutil.move(tmpFilename, categoryFilename)

        if found == 'true':
            logger.info("xmDeleteCategory - Successfully Deleted Category (category): " + category)
            print ("Success")
        else:
            logger.info("xmDeleteCategory - Failure Deleting Category (category): " + category)
            print ("Failure")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)


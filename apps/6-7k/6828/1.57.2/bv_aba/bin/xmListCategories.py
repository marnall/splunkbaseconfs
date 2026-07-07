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

    try:

        # Get property for categories.filename
        propertyFilename = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "categories.filename":
                    propertyFilename = propval[:-1]

        with open(propertyFilename) as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                print (row[0])

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)


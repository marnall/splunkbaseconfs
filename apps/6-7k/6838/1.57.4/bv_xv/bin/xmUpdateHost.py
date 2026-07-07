# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os
import platform
import time
import sys
import shutil
import splunk.Intersplunk as si
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    ipAddress = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "ab"
    if python3:
        rmode = "r"
        wmode = "a"

    try:

        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                ipAddress = arg
        else:
            raise Exception('xmUpdateHost-F-001: Usage: xmUpdateHost ipaddress')

        print ('Result')
        splunkHome=os.environ.get('SPLUNK_HOME')
        propertiesFilename = splunkHome + "/etc/apps/bv_xv/config/scm-framework.properties"
        tmpFilename = splunkHome + "/etc/apps/bv_xv/config/scm-framework.temp"

        separator = "="
        keys = {}

        with open(tmpFilename,"w") as tmpFile:
            with open(propertiesFilename) as f:
                for line in f:
                    if line.strip().startswith('#'):
                        tmpFile.write(line)
                    else:
                        if separator in line:
                            name, value = line.split(separator, 1)
                            if name == 'mongo.host':
                                tmpFile.write(name+'='+ipAddress+'\n')
                            elif name == 'splunk.rest.ipAddress':
                                tmpFile.write(name+'='+ipAddress+'\n')
                            else:
                                tmpFile.write(line)
                        else:
                            tmpFile.write(line)

        shutil.move(tmpFilename, propertiesFilename)
        print ("Success")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

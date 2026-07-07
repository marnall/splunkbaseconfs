# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import sys
import saUtils
import splunk.Intersplunk as si
import os
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

splunkHome=os.environ.get('SPLUNK_HOME')

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("resourceLookup starting, args [" + repr(sys.argv) + "]");
    logging.info("args count [" + str(len(sys.argv)) + "]");

#    print str(len(sys.argv))

    try:

        logging.info("Calling resourceLookup")

        saUtils.runProcess(sys.argv[0], "resourceLookup", argList, False)

        logging.info ("-------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

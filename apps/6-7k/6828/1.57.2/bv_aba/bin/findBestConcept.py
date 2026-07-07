# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to persist signals read from stdin to a file which
# can then be setup in splunk as a data source and persisted and persisted
# to an index.
#
import sys
import saUtils
import splunk.Intersplunk as si
import os
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("findBestConcept starting, args [" + repr(sys.argv) + "]");

    try:
        logging.info("calling findBestConcept")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "findBestConcept", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

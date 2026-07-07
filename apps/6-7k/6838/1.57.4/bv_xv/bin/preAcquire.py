# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
import sys
import saUtils
import splunk.Intersplunk as si
import os
import saDbUtils
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "preAcquire\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    payload = ''
    parameters = ''
    lastArg=''
    logging.info("---------------------------------------------------------------------------------------")
    #logging.info("SPLUNK_HOME: " + os.environ["SPLUNK_HOME"])
    #logging.info("LD_LIBRARY_PATH: " + os.environ["LD_LIBRARY_PATH"])
    #logging.info("Current Dir: " + os.path.dirname(os.path.realpath(__file__)))
    logging.info("preAcquire starting, args " + repr(sys.argv) + "]")

    try:
        if len(sys.argv) != 1:
            usage ("Too many arguments!")

        logging.info("Calling preAcquire with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "preAcquire", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        logging.info("Exception in preAcquire:")
        logging.info(e)
        si.generateErrorResults(e)

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

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "xmListLicense [<applicationType>]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListLicense starting, args " + repr(sys.argv) + "]");

    try:

        if len(sys.argv) > 2:
            usage ("Too many arguments!");

        argList = []
        if len(sys.argv) == 2:
            argList.append ("-a");
            argList.append (sys.argv[1]);

        logging.info("Calling xmListLicense with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListLicense", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

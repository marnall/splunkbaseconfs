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

    usageStatement = "xmSyncCredentials REST_IP <shHost>\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    restIp = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmSyncCredentials starting, args " + repr(sys.argv) + "]");

    try:

        if len(sys.argv) != 3:
            usage ("Too few arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "rest_ip":
                lastArg="restIp"
            elif lastArg == "restIp":
                restIp=arg;

        argList.append ("-h");
        argList.append (restIp);
        
        logging.info("Calling xmSyncCredentials with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmSyncCredentials", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

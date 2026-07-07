# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
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
        logging.error (message);

    usageStatement = "search | runExtremeRules RULE_PACKAGE rulePackageName APPLICATION (XVAW | XR | ABA)  [SIGNAL (true | false)] [QUERY expression [QUERY_ALPHACUT (0-1)] [CONTAINER containerName CONTEXT contextName]] [MODEL modelNameForSignals] \n";
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("runExtremeRules starting, args [" + repr(sys.argv) + "]");
    logging.info("args count [" + str(len(sys.argv)) + "]");

#    print str(len(sys.argv))

    try:

        logging.info("Calling runExtremeRules")

        saUtils.runProcess(sys.argv[0], "runExtremeRules", argList, False)

        logging.info ("-------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

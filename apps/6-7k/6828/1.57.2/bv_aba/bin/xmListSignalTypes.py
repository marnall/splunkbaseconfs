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

    usageStatement = "Version 1: xmListSignalTypes MODEL_NAME modelName PACKAGE_NAME rulePackageName [VERSION 1]\nVersion 2: xmListSignalTypes PACKAGE_NAME rulePackageName APPLICATION (XVAW | XR | ABA) VERSION 2";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    category = ''
    source = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListSignalTypes starting, args " + repr(sys.argv) + "]");

    try:

        for arg in sys.argv[1:]:
            if arg.lower() == "category":
                lastArg = "category";
            elif arg.lower() == "source":
                lastArg="source"
            elif lastArg == "category":
                category = arg
                lastArg = '';
            elif lastArg == "source":
                source = arg
                lastArg = '';
            else:
                usage ("Invalid Argument:" + arg)

        if len (category) > 0:
            argList.append ("-c");
            argList.append (category)

        if len (source) > 0:
            argList.append ("-s");
            argList.append (source)

        logging.info("Calling xmListSignalTypes with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListSignalTypes", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmListRulePackages [modelName modelName] [VERSION (1|2)] [APPLICATION (XVAW | XR | ABA)]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    version = '1'
    application = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListRulePackages starting, args " + repr(sys.argv) + "]");

    try:
        for arg in sys.argv[1:]:
            if arg.lower() == "model_name":
                lastArg = "modelName";
            elif arg.lower() == "version":
                lastArg="version"
            elif arg.lower() == "application":
                lastArg="application"
            elif lastArg == "modelName":
                modelName = arg
                lastArg = '';
            elif lastArg == "version":
                version = arg
                lastArg = '';
            elif lastArg == "application":
                application = arg
                lastArg = '';
            else:
                usage ("Invalid Argument:" + arg)

        if len (modelName) > 0:
            argList.append ("-m");
            argList.append (modelName)

        if len (application) > 0:
            argList.append ("-a");
            argList.append (application)

        argList.append ("--version");
        argList.append (version);

        logging.info("Calling xmListRulePackages with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListRulePackages", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

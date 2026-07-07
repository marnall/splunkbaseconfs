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

    usageStatement = "xmDiscoverPeerGroups modelName [ANALYSISNAME \"name\"] [SIGNALPROPS \"name=value1|name2=value2\"]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    analysisName = ''
    signalProps = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmDiscoverPeerGroups starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Incorrect number of arguments!")

        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg = "analysisName";
            elif arg.lower() == "signalprops":
                lastArg="signalProps"
            elif lastArg == "analysisName":
                analysisName = arg
                lastArg = ''
            elif lastArg == "signalProps":
                signalProps = arg
                lastArg = ''
            else:
                usage ("Invalid argument: " + arg);

        modelName = sys.argv[1];
        argList.append("-m")
        argList.append (modelName)

        if len(analysisName) > 0:
            argList.append ("-n");
            argList.append (analysisName);

        if len(signalProps) > 0:
            argList.append ("-P");
            argList.append (signalProps);

        logging.info("Calling xmDiscoverPeerGroups with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmDiscoverPeerGroups", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

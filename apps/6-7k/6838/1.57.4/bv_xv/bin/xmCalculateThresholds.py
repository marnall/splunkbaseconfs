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

    usageStatement = "xmCalculateThresholds modelName [ANALYSISNAME name] [force ('true' | 'false')]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    analysisName = ''
    signalProps = ''
    lastArg = ''
    force='false'
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmCalculateThresholds starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")

        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif arg.lower() == "force":
                lastArg="force"
            elif lastArg == "analysisname":
                analysisName = arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps = arg
                lastArg=''
            elif lastArg == "force":
                force=arg
                lastArg=''

        modelName = sys.argv[1];
        argList.append("-m")
        argList.append (modelName)

        if len(analysisName) > 0:
            argList.append("-n");
            argList.append(analysisName)

        if len(signalProps) > 0:
            argList.append("-p");
            argList.append(signalProps)

        if force.lower() == 'true':
            argList.append("-f")

        logging.info("Calling xmCalculateThresholds with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmCalculateThresholds", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

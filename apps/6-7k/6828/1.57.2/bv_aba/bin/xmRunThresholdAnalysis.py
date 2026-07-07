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

    usageStatement = "xmRunThresholdAnalysis modelName [ANALYSISNAME name] [SIGNALPROPS \"prop1=value1|prop2=value2\" ]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    analysisName = ''
    signalProps= ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRunThresholdAnalysis starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")

        modelName = sys.argv[1];

        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif lastArg == "analysisname":
                analysisName = arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        argList.append("-m"); 
        argList.append(modelName);

        if len(analysisName) > 0:
            argList.append("-n"); 
            argList.append(analysisName)

        if len(signalProps) > 0:
            argList.append("-p"); 
            argList.append(signalProps)

        logging.info("Calling xmRunThresholdAnalysis with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRunThresholdAnalysis", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmRunAnomalyRules modelName RULE_PACKAGE rulePackageName STARTDATE fromDate ENDDATE toDate [ANALYSISNAME name] [SIGNALPROPS \"prop1=value1|prop2=value2|...\"]\nSTARTDATE: \"mm/dd/yyyy hh:mm:ss\" or EPOCH\nENDDATE \"mm/dd/yyyy hh:mm:ss\" or EPOCH\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName =''
    rulePackageName=''
    fromDate=''
    toDate=''
    analysisName=''
    signalProps=''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRunAnomalyRules starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 8:
            usage ("Not enough arguments!")

        for arg in sys.argv[2:]:
            if arg.lower() == "rule_package":
                lastArg="rule_package"
            elif arg.lower() == "startdate":
                lastArg="startdate"
            elif arg.lower() == "enddate":
                lastArg="enddate"
            elif arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif lastArg == "rule_package":
                rulePackageName=arg
                lastArg=''
            elif lastArg == "startdate":
                fromDate=arg
                lastArg=''
            elif lastArg == "enddate":
                toDate=arg
                lastArg=''
            elif lastArg == "analysisname":
                analysisName=arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps=arg
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

        modelName = sys.argv[1];

        argList.append("-m")
        argList.append (modelName)
        argList.append("-p")
        argList.append (rulePackageName)
        argList.append("-f")
        argList.append (fromDate)
        argList.append("-t")
        argList.append (toDate)

        if len(analysisName) > 0:
            argList.append ("-a");
            argList.append (analysisName);

        if len(signalProps) > 0:
            argList.append ("-P");
            argList.append (signalProps);

        logging.info("Calling xmRunAnomalyRules with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRunAnomalyRules", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

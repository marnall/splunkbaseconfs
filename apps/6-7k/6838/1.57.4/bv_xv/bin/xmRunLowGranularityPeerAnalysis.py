# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to run peer to peer actor analsysis.
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

    usageStatement = "xmRunLowGranularityPeerAnalysis modelName [STARTDATE (mm/dd/yyyy OR epoch)] [NUM_PERIODS_PER_DAY (1 | 2 | 6)] [ANALYSISNAME name] [SIGNALPROPS \"prop1=value2|prop2=value2|...\"] [FORCE true | false]"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmRunLowGranularityPeerAnalysis starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 2:
        usage ("Not enought arguments!")

    lastArg='';
    startDate='';
    lookBackDays='';
    daysInterval='';
    analysisName='';
    signalProps='';
    force='false';
    numPeriodsPerDay='';
    modelName = sys.argv[1];

    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif arg.lower() == "force":
                lastArg="force"
            elif arg.lower() == "startdate":
                lastArg="startDate"
            elif arg.lower() == "num_periods_per_day":
                lastArg="numPeriodsPerDay"
            elif arg.lower() == "look_back_days":
                lastArg="lookBackDays"
            elif arg.lower() == "days_interval":
                lastArg="daysInterval"
            elif lastArg == "analysisname":
                analysisName=arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps=arg
                lastArg=''
            elif lastArg == "force":
                force=arg
                lastArg=''
            elif lastArg == "startDate":
                startDate=arg
                lastArg=''
            elif lastArg == "numPeriodsPerDay":
                numPeriodsPerDay=arg
                lastArg=''
            elif lastArg == "lookBackDays":
                lookBackDays=arg
                lastArg=''
            elif lastArg == "daysInterval":
                daysInterval=arg
                lastArg=''
            else:
                usage ("Unrecognized argument: " + arg)

    argList.append ("-m")
    argList.append (modelName)

    if len (numPeriodsPerDay) > 0:
        argList.append ("-p");
        argList.append (numPeriodsPerDay);

    if len (lookBackDays) > 0:
        argList.append ("-l");
        argList.append (lookBackDays);

    if len (daysInterval) > 0:
        argList.append ("-i");
        argList.append (daysInterval);

    if len (startDate) > 0:
        argList.append ("-d");
        argList.append (startDate);

    if len (analysisName) > 0:
        argList.append ("-n")
        argList.append (analysisName)

    if len (signalProps) > 0:
        argList.append ("-P");
        argList.append (signalProps);

    if force.lower() == "true":
        argList.append("-F");

    logging.info("xmRunLowGranularityPeerAnalysis processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmRunLowGranularityPeerAnalysis with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmRunLowGranularityPeerAnalysis", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

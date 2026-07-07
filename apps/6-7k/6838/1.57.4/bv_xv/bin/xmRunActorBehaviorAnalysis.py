# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to run the actor behavior change analysis command.
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

    usageStatement = "xmRunActorBehaviorAnalysis modelName [ANALYSISNAME name] [ACTORID actorId] [STARTDATE mm/dd/yyyy] [SIGNALPROPS prop1=value1|prop2=value2|...]"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmRunActorBehaviorAnalysis starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 2:
        usage ("Not enought arguments!")

    lastArg='';
    analysisName='';
    signalProps='';
    actorId='';
    startDate='';
    modelName = sys.argv[1];
    argList.append("-m");
    argList.append (modelName);

    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "actorid":
                lastArg="actorId"
            elif arg.lower() == "startdate":
                lastArg="startdate"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif lastArg == "analysisname":
                analysisName=arg
                lastArg=''
            elif lastArg == "actorId":
                actorId=arg
                lastArg=''
            elif lastArg == "startdate":
                startDate=arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps=arg
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

    argList.append("-m")
    argList.append(modelName)

    if len(analysisName) > 0:
        argList.append("-n")
        argList.append(analysisName)

    if len(actorId) > 0:
        argList.append("-a");
        argList.append(actorId);

    if len(startDate) > 0:
        argList.append("-d");
        argList.append(startDate);

    if len(signalProps) > 0:
        argList.append("-p");
        argList.append(signalProps);

    logging.info("xmRunActorBehaviorAnalysis processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmRunActorBehaviorAnalysis with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmRunActorBehaviorAnalysis", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

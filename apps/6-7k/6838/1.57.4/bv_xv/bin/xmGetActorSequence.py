# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to extract events that fall into a specified time period 
# of a certain taxonomy from an actors landscape model. 
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

    usageStatement = "xmGetActorSequence <modelName> ACTOR <actorId> [REF_KEY <referenceKey>] [[FROMDATE \"<EPOCH or MM/DD/YYYY HH:MM:SS or Splunk (-1d@d)>\" TODATE \"<EPOCH or MM/DD/YYYY HH:MM:SS or Splunk (-1d@d)>\"] | [TAXONOMYID <endEventTaxonomyId> EVENTTIME <endEventTimeEpoch> [NUMNODES <numNodesToReturn> | TODATE MM/DD/YYYY] [NUMNODESAFTER <numNodesAfterEndEventTaxonomyId>]]"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmGetActorSequence starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 3:
        usage ("Not enought arguments!")

    modelName = sys.argv[1];
    actor='';
    refKey='';
    fromDate='';
    toDate='';
    taxonomyId='';
    eventTime='';
    numNodes='';
    numNodesAfter='';
    lastArg='';

    for arg in sys.argv[2:]:
        if arg.lower() == "actor":
            lastArg="actor"
        elif arg.lower() == "ref_key":
            lastArg="refKey"
        elif arg.lower() == "taxonomyid":
            lastArg="taxonomyId"
        elif arg.lower() == "eventtime":
            lastArg="eventTime"
        elif arg.lower() == "numnodes":
            lastArg="numNodes"
        elif arg.lower() == "numnodesafter":
            lastArg="numNodesAfter"
        elif arg.lower() == "fromdate":
            lastArg="fromDate"
        elif arg.lower() == "todate":
            lastArg="toDate"
        elif lastArg == "actor":
            actor=arg
            lastArg=''
        elif lastArg == "refKey":
            refKey=arg
            lastArg=''
        elif lastArg == "taxonomyId":
            taxonomyId=arg
            lastArg=''
        elif lastArg == "eventTime":
            eventTime=arg
            lastArg=''
        elif lastArg == "numNodes":
            numNodes=arg
            lastArg=''
        elif lastArg == "numNodesAfter":
            numNodesAfter=arg
            lastArg=''
        elif lastArg == "fromDate":
            fromDate=arg
            lastArg=''
        elif lastArg == "toDate":
            toDate=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len(actor) == 0:
        usage ("Missing argument: actor <actorId>");
    elif len(eventTime) == 0 and len(fromDate) == 0:
        usage ("Missing argument: eventTime <eventTime> or fromDate <mm/dd/yyyy>");
    elif len(numNodes) == 0 and len(toDate) == 0:
        usage ("Missing argument: numNodes <numNodes> OR toDate <mm/dd/yyyy>");
    # Let the Executable handle the remaining validity checks.

    argList.append("-m")
    argList.append(modelName)

    argList.append("-a")
    argList.append(actor)

    if len(refKey) > 0:
        argList.append("-r")
        argList.append(refKey)

    if len(taxonomyId) > 0:
        argList.append("-e")
        argList.append(taxonomyId)

    if len (eventTime) > 0:
        argList.append("-t")
        argList.append(eventTime)
    
    if len(numNodes) > 0:
        argList.append("-n")
        argList.append(numNodes)

    if len(numNodesAfter) > 0:
        argList.append("-N")
        argList.append(numNodesAfter)

    if len(fromDate) > 0:
        argList.append ("-f")
        argList.append (fromDate);

    if len(toDate) > 0:
        argList.append ("-T")
        argList.append(toDate)

    logging.info("xmGetActorSequence processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmGetActorSequence with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmGetActorSequence", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

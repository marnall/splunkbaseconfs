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

    usageStatement = "xmQueryActorSequence <modelName> ACTOR <actorId> DAY_OF_WEEK < 0 - 6 > START_NODE <action~process~field> END_NODE <action~process~field> [THRU_NODES <action~process~field[,action~process~field,...]> [NOT_THRU_NODES <action~process~field[,action~process~field,...]> [FILTER_TYPE (search | highProbability | lowProbability | shortest)] [FILTER_ARG arg]\nDAYOFWEEK: 0 = Sunday, 1 = Monday, ... 6 = Saturday\nFILTER_ARG: for highest and lowest filter type, arg is alfacut (between 0 and 1) for how far out from probability to display matching paths (default .05) and for shortest the number of paths to display (default 1)"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmQueryActorSequence starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 3:
        usage ("Not enought arguments!")

    actor='';
    dayOfWeek='';
    startTaxon='';
    endTaxon='';
    thruTaxons='';
    notThruTaxons='';
    filterType='search';
    filterArg='';
    lastArg='';
    modelName = sys.argv[1];

    for arg in sys.argv[2:]:
        if arg.lower() == "actor":
            lastArg="actor"
        elif arg.lower() == "day_of_week":
            lastArg="dayofweek"
        elif arg.lower() == "start_taxon" or arg.lower() == "start_node":
            lastArg="starttaxon"
        elif arg.lower() == "end_taxon" or arg.lower() == "end_node":
            lastArg="endtaxon"
        elif arg.lower() == "thru_taxons" or arg.lower() == "thru_nodes":
            lastArg="thrutaxons"
        elif arg.lower() == "not_thru_taxons" or arg.lower() == "not_thru_nodes":
            lastArg="notthrutaxons"
        elif arg.lower() == "filter_type":
            lastArg="filtertype"
        elif arg.lower() == "filter_arg":
            lastArg="filterarg"
        elif lastArg == "actor":
            actor=arg
            lastArg=''
        elif lastArg == "dayofweek":
            dayOfWeek=arg
            lastArg=''
        elif lastArg == "starttaxon":
            startTaxon=arg
            lastArg=''
        elif lastArg == "endtaxon":
            endTaxon=arg
            lastArg=''
        elif lastArg == "thrutaxons":
            thruTaxons=arg
            lastArg=''
        elif lastArg == "notthrutaxons":
            notThruTaxons=arg
            lastArg=''
        elif lastArg == "filtertype":
            filterType=arg
            lastArg=''
        elif lastArg == "filterarg":
            filterArg=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len(actor) == 0:
        usage ("Missing argument: actor <actorId>");
    if len(dayOfWeek) == 0:
        usage ("Missing argument: DayOfWeek 0 - 6 (0 or 1 or 2 or 3 or 4 or 5 or 6)");
    if len(startTaxon) == 0:
        usage ("Missing argument: START_NODE Action~Process~Field");
    if len(endTaxon) == 0:
        usage ("Missing argument: END_NODE Action~Process~Field");

    # Let the Executable handle the remaining validity checks.

    argList.append("-m")
    argList.append(modelName)

    argList.append("-a")
    argList.append(actor)

    argList.append("-d")
    argList.append(dayOfWeek)

    argList.append("-s")
    argList.append(startTaxon)

    argList.append("-e")
    argList.append(endTaxon)

    if len(thruTaxons) > 0:
        argList.append("-t")
        argList.append(thruTaxons)

    if len(notThruTaxons) > 0:
        argList.append("-n")
        argList.append(notThruTaxons)

    if len(filterType) > 0:
        argList.append("-f")
        argList.append(filterType)

    if len(filterArg) > 0:
        argList.append("-A")
        argList.append(filterArg)

    logging.info("xmQueryActorSequence processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmQueryActorSequence with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmQueryActorSequence", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmListQuotaUsage APPLICATION <applicationType> [FROMDATE \"<EPOCH or MM/DD/YYYY HH:MM:SS or Splunk (-1d@d)>\" TODATE \"<EPOCH or MM/DD/YYYY HH:MM:SS or Splunk (-1d@d)>\"]"; 
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmListQuotaUsage starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 3:
        usage ("Not enought arguments!")

    modelName = sys.argv[1];
    application ='';
    fromDate='';
    toDate='';
    lastArg='';

    for arg in sys.argv[1:]:
        if arg.lower() == "application":
            lastArg="application"
        elif arg.lower() == "fromdate":
            lastArg="fromDate"
        elif arg.lower() == "todate":
            lastArg="toDate"
        elif lastArg == "application":
            application=arg
            lastArg=''
        elif lastArg == "fromDate":
            fromDate=arg
            lastArg=''
        elif lastArg == "toDate":
            toDate=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len(application) == 0:
        usage ("Missing argument: APPLICATION <applicationType>");

    argList.append("-a")
    argList.append(application)

    if len(fromDate) > 0:
        argList.append ("-f")
        argList.append (fromDate);

    if len(toDate) > 0:
        argList.append ("-t")
        argList.append(toDate)

    logging.info("xmListQuotaUsage processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmListQuotaUsage with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmListQuotaUsage", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

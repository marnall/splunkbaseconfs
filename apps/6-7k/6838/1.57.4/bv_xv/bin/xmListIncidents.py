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

    usageStatement = "xmListIncidents TYPE (FRAUD | BEHAVIOR | OTHER_VALID_APP_TYPE) [EARLIEST \"-1d@d\" LATEST \"0d@d\"] [STATUS (NEW | IN_PROGRESS | PENDING | RESOLVED | CLOSED)] [OWNER <ownerUserId>]"

    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmListIncidents starting, args [" + repr(sys.argv) + "]");

    earliest='';
    latest='';
    status='';
    owner='';
    type='';
    lastArg='';

    for arg in sys.argv[1:]:
        if arg.lower() == "earliest":
            lastArg="earliest"
        elif arg.lower() == "latest":
            lastArg="latest"
        elif arg.lower() == "status":
            lastArg="status"
        elif arg.lower() == "owner":
            lastArg="owner"
        elif arg.lower() == "type":
            lastArg="type"
        elif lastArg == "earliest":
            earliest=arg
            lastArg=''
        elif lastArg == "latest":
            latest=arg
            lastArg=''
        elif lastArg == "status":
            status=arg
            lastArg=''
        elif lastArg == "owner":
            owner=arg
            lastArg=''
        elif lastArg == "type":
            type=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len(earliest) > 0 and len(latest) > 0:
        argList.append ("-f");
        argList.append (earliest);
        argList.append ("-t");
        argList.append (latest);

    if len(status) > 0:
        argList.append ("-s");
        argList.append (status);

    if len(owner) > 0:
        argList.append ("-o");
        argList.append (owner);

    if len(type) > 0:
        argList.append ("-T");
        argList.append (type);
    else:
        usage ("type (appType) required!");

    try:
        logging.info("calling xmListIncidents with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmListIncidents", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

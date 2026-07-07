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

    usageStatement = "xmAddNoteToIncident <signalGuid> <type: BEHAVIOR | FRAUD> <urlEncodedNoteText>"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmAddNoteToIncident starting, args [" + repr(sys.argv) + "]");

    signalGuid='';
    owner='';

    if len(sys.argv) != 4:
       usage ("not enough arguments") 

    argList.append ("-g");
    argList.append (sys.argv[1]);

    argList.append ("-t");
    argList.append (sys.argv[2]);

    argList.append ("-n");
    argList.append (sys.argv[3]);

    try:
        logging.info("calling xmAddNoteToIncident with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmAddNoteToIncident", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

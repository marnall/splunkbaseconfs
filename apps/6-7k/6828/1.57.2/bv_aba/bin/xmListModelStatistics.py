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

    usageStatement = "xmListModelStatistics MODEL_NAME <modelName> [MAX_RECORDS <maxRecords default 30>]";
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmListModelStatistics starting, args [" + repr(sys.argv) + "]");

    modelName='';
    maxRecords='30';
    lastArg='';

    for arg in sys.argv[1:]:
        if arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "max_records":
            lastArg="maxRecords"
        elif lastArg == "modelName":
            modelName=arg
            lastArg=''
        elif lastArg == "maxRecords":
            maxRecords=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len(modelName) > 0:
        argList.append("-m")
        argList.append(modelName)

    argList.append ("-M")
    argList.append (maxRecords)

    logging.info ("xmListModelStatistics processed args, modelName: [" + modelName + "], maxRecords: (" + maxRecords + ")")

    try:
        logging.info("calling xmListModelStatistics with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmListModelStatistics", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

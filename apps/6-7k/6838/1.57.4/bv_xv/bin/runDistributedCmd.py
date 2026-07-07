# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is an example of one that uses a pre-op to generate data.
# It runs xsPreListDir to generate data and then invokes xsListDir to
# process the data.
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
    
    usageStatement = "runDistributedCmd cmd urlEncodedCmd [parameters 'param1:value1,param2:param2'] [targets 'idx-1 idx-2 idx-3']\n";
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);


if __name__ == '__main__':


    argList = []
    cmd = ''
    parameters = ''
    targets = ''
    lastArg = ''
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("runDistributedCmd starting");

    if len(sys.argv) < 3:
        usage ("Not enough arguments!")

    for arg in sys.argv[1:]:
        if arg.lower() == "cmd":
            lastArg="cmd"
        elif arg.lower() == "parameters":
            lastArg="parameters"
        elif arg.lower() == "targets":
            lastArg="targets"
        elif lastArg == "cmd":
#            cmd = saUtils.appendWithSpace (arg, cmd)
            cmd = arg;
            lastArg = '';
        elif lastArg == "parameters":
            parameters = saUtils.appendWithSpace (arg, parameters)
            lastArg = '';
        elif lastArg == "targets":
            targets = arg;
            lastArg = '';
        else:
            usage ("Invalid Argument:" + arg)

    if len(cmd) > 0:
        argList.append("-c");
        argList.append (cmd);

    if len(parameters) > 0:
        argList.append("-p");
        argList.append (parameters);

    if len(targets) > 0:
        argList.append("-t");
        argList.append (targets);

    logging.info("runDistributedCmd starting");

    try:
        
        #logging.info("Calling runDistributedCmd with args: " + repr (argList))
        #logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "runDistributedCmd", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

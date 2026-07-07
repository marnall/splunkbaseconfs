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

    usageStatement = "xmCreateTransaction NAME transactionName [PROPS prop1=value1|prop2=value2|...]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    transactionName = ''
    props = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmCreateTransaction starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 3:
            usage ("Too few arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "name":
                lastArg="name"
            elif arg.lower() == "props":
                lastArg="props"
            elif lastArg == "name":
                transactionName = arg
                lastArg=''
            elif lastArg == "props":
                props = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(transactionName) > 0:
            argList.append("-t");
            argList.append(transactionName)
        else:
            usage ("Missing argument: NAME transactionName");

        if len(props) > 0:
            argList.append("-P");
            argList.append(props)

        logging.info("Calling xmCreateTransaction with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmCreateTransaction", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

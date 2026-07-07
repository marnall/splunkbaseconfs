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

    usageStatement = "xmListContext [CONTAINER containerName] [NAME contextName] [CLASS className] [LIMIT maxToReturn]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    application = ''
    containerName = ''
    contextName = ''
    className = ''
    emptyClass = False
    limit = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListContext starting, args " + repr(sys.argv) + "]");

    try:

        if len(sys.argv) > 11:
            usage ("Too many arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "container":
                lastArg="container"
            elif arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "name":
                lastArg="name"
            elif arg.lower() == "class":
                lastArg="class"
            elif arg.lower() == "limit":
                lastArg="limit"
            elif lastArg == "container":
                containerName = arg
                lastArg=''
            elif lastArg == "application":
                application = arg
                lastArg=''
            elif lastArg == "name":
                contextName = arg
                lastArg=''
            elif lastArg == "class":
                className = arg
                if len(className) == 0:
                    emptyClass = True;
                lastArg=''
            elif lastArg == "limit":
                limit = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(application) > 0:
            argList.append("-A")
            argList.append (application)

        if len(containerName) > 0:
            argList.append("-c")
            argList.append (containerName)

        if len(contextName) > 0:
            argList.append("-n")
            argList.append (contextName)

        if emptyClass or len(className) > 0:
            argList.append("-C")
            argList.append (className)

        if len(limit) > 0:
            argList.append("-l")
            argList.append(limit)

        logging.info("Calling xmListContext with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListContext", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

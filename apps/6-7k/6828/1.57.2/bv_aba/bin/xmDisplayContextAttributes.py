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

    usageStatement = "xmDisplayContextAttributes [APPLICATION app] CONTAINER containerName CONTEXT contextName [CLASSNAME className]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    application = ''
    containerName = ''
    contextName = ''
    className = ''
    emptyClass = False
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmDisplayContextAttributes starting, args " + repr(sys.argv) + "]");

    try:
        for arg in sys.argv[1:]:
            if arg.lower() == "container":
                lastArg="container"
            elif arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "context":
                lastArg="context"
            elif arg.lower() == "classname":
                lastArg="classname"
            elif lastArg == "application":
                application=arg
                lastArg=''
            elif lastArg == "container":
                containerName=arg
                lastArg=''
            elif lastArg == "context":
                contextName=arg
                lastArg=''
            elif lastArg == "classname":
                className=arg
                if len(className) == 0:
                    emptyClass = True;
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

        if len(containerName) == 0:
            usage ("missing argument CONTAINER containerName");

        if len(contextName) == 0:
            usage ("missing argument CONTEXT contextName");

        argList.append("-C")
        argList.append (containerName)

        argList.append("-n")
        argList.append (contextName)

        if len(application) > 0:
            argList.append ("-A")
            argList.append (application)

        if emptyClass or len(className) > 0:
            argList.append ("-Y")
            argList.append (className)

        logging.info("Calling xmDisplayContextAttributes with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmDisplayContextAttributes", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

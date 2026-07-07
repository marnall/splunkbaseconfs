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

    usageStatement = "xmUpdateContext APPLICATION application CONTAINER containerName CONTEXT contextName SAVED_SEARCH_NAME searchNameName SEARCH_EARLIEST \"-31d@d\" SEARCH_LATEST=\"-1d@d\"";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    application = ''
    context = ''
    context = ''
    savedSearchName = ''
    searchEarliest = ''
    searchLatest = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmUpdateContext starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 9 or len(sys.argv) > 13:
            usage ("Incorrect number of arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "container":
                lastArg="container"
            elif arg.lower() == "context":
                lastArg="context"
            elif arg.lower() == "saved_search_name":
                lastArg="search"
            elif arg.lower() == "search_earliest":
                lastArg="earliest"
            elif arg.lower() == "search_latest":
                lastArg="latest"
            elif lastArg == "application":
                application = arg
                lastArg=''
            elif lastArg == "container":
                container = arg
                lastArg=''
            elif lastArg == "context":
                context = arg
                lastArg=''
            elif lastArg == "search":
                savedSearchName = arg
                lastArg=''
            elif lastArg == "earliest":
                searchEarliest = arg
                lastArg=''
            elif lastArg == "latest":
                searchLatest = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(application) > 0:
            argList.append("-a");
            argList.append(application)
        else:
            usage ("Missing argument APPLICATION application (i.e. XVAW, XR, or ABA)");

        if len(container) > 0:
            argList.append("-C"); 
            argList.append(container)
        else:
            usage ("Missing argument CONTAINER containerName ");

        if len(context) > 0:
            argList.append("-c"); 
            argList.append(context)
        else:
            usage ("Missing argument CONTEXT contextName");

        if len(savedSearchName) == 0 and len(searchEarliest) == 0 and len(searchLatest) == 0:
            usage ("Must specific at least one of these options: SAVED_SEARCH_NAME name SEACH_EARLIEST earliest OR SEARCH_LATEST latest"); 

        if len(savedSearchName) > 0:
            argList.append("-s");
            argList.append(savedSearchName)

        if len(searchEarliest) > 0:
            argList.append("-e");
            argList.append(searchEarliest)

        if len(searchLatest) > 0:
            argList.append("-l");
            argList.append(searchLatest)

        logging.info("Calling xmUpdateContext with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmUpdateContext", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

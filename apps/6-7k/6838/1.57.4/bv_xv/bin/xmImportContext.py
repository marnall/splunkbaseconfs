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

    usageStatement = "xmImportContext CONTAINER containerName APPLICATION (XVAW | XR | ABA) FILE importFileName.csv\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    application = ''
    containerName = ''
    fileName = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmImportContext starting, args " + repr(sys.argv) + "]");

    try:
        for arg in sys.argv[1:]:
            if arg.lower() == "container":
                lastArg="container"
            elif arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "file":
                lastArg="file"
            elif lastArg == "container":
                containerName=arg
                lastArg=''
            elif lastArg == "application":
                application=arg
                lastArg=''
            elif lastArg == "file":
                fileName=arg
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

        if len(containerName) == 0:
            usage ("missing argument CONTAINER containerName");

        if len(fileName) == 0:
            usage ("missing argument FILE importFileName.csv");

        if len(application) > 0:
            argList.append("-A")
            argList.append (application)

        argList.append("-c")
        argList.append (containerName)

        argList.append("-f")
        argList.append (fileName)

        logging.info("Calling xmImportContext with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmImportContext", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

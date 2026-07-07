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

splunkHome=os.environ.get('SPLUNK_HOME')

# Set LD_LIBRARY_PATH to point to the install's lib directory.
#os.environ["LD_LIBRARY_PATH"] = splunkHome + "/etc/apps/bv_aba/lib"
#os.environ["DYLD_LIBRARY_PATH"] = splunkHome + "/etc/apps/bv_aba/lib"

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "xmDeleteContext containerName APPLICATION (XVAW | XR | ABA) [CONTEXT contextName1[,contextName2,...]] [CLASS className1[,className2]]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    containerName = ''
    contextNames = ''
    classNames = ''
    application = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmDeleteContext starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")
        elif len(sys.argv) > 8:
            usage ("Too many arguments!")

        containerName = sys.argv[1];

        for arg in sys.argv[2:]:
            if arg.lower() == "context":
                lastArg="context"
            elif arg.lower() == "class":
                lastArg="class"
            elif arg.lower() == "application":
                lastArg="application"
            elif lastArg == "context":
                contextNames = arg
                lastArg=''
            elif lastArg == "class":
                classNames = arg
                lastArg=''
            elif lastArg == "application":
                application = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(containerName) > 0:
            argList.append("-c")
            argList.append(containerName)
        else:
            usage ("Missing argument: containerName");

        if len(application) > 0:
            argList.append("-A")
            argList.append(application)

        if len(contextNames) > 0:
            argList.append("-C")
            argList.append(contextNames)

        if len(classNames) > 0:
            argList.append("-n")
            argList.append (classNames)

        logging.info("Calling xmDeleteContext with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmDeleteContext", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

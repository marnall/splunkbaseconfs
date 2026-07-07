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

    usageStatement = "xmCreateModel MODEL_NAME modelName APPLICATION appType [PROPS 'prop1=value1|prop2=value2'\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName=''
    app=''
    props=''
    lastArg=''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmCreateModel starting, args " + repr(sys.argv) + "]");

    if len(sys.argv) < 5:
        usage ("Incorrect number of args!");

    for arg in sys.argv[1:]:
        if arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "application":
            lastArg="app"
        elif arg.lower() == "props":
            lastArg="props"
        elif lastArg == "modelName":
            modelName=arg
            lastArg=''
        elif lastArg == "app":
            app=arg
            lastArg=''
        elif lastArg == "props":
            props=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    argList.append ("-m");
    argList.append (modelName);

    argList.append ("-a");
    argList.append (app);

    if len(props) > 0:
        argList.append ("-p");
        argList.append (props);

    try:
        logging.info("Calling xmCreateModel with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmCreateModel", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

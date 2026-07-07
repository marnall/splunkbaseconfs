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

    usageStatement = "xmMapResources FILE inputFileName MAPPING mappingName [MODEL modelName] [REMOVEINPUT <true | *false>] [SAVEOUTPUT <*true | false>] [APPENDOUTPUT <true | *false>] \n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    inputFile=''
    mappingName=''
    modelName=''
    removeInput='false'
    saveOutput='true'
    appendOutput='false'
    lastArg=''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmMapResources starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 5:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "file":
                lastArg="file"
            elif arg.lower() == "mapping":
                lastArg="mapping"
            elif arg.lower() == "model":
                lastArg="model"
            elif arg.lower() == "removeinput":
                lastArg="removeinput"
            elif arg.lower() == "saveoutput":
                lastArg="saveoutput"
            elif arg.lower() == "appendoutput":
                lastArg="appendoutput"
            elif lastArg == "file":
                inputFile=arg
                lastArg=''
            elif lastArg == "mapping":
                mappingName=arg
                lastArg=''
            elif lastArg == "model":
                modelName=arg
                lastArg=''
            elif lastArg == "removeinput":
                removeInput=arg
                lastArg=''
            elif lastArg == "saveoutput":
                saveOutput=arg
                lastArg=''
            elif lastArg == "appendoutput":
                appendOutput=arg
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

        argList.append("-f")
        argList.append (inputFile)
        argList.append("-m")
        argList.append (mappingName)
        argList.append("-r")
        argList.append (removeInput)
        argList.append("-s")
        argList.append (saveOutput)
        argList.append("-a")
        argList.append (appendOutput)
        if len(modelName) > 0:
            argList.append ("-M");
            argList.append (modelName);

        logging.info("Calling xmMapResources with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmMapResources", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)


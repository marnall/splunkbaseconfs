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

    usageStatement = "xmImportGraphs MODEL_NAME <modelName> FILE <fileName> [REPLACE (true | false)]\nREPLACE - if present all rule packages referenced in the import file will be replaced, if not present any graphs already present in the database but refernced will be ignored during import."
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmImportGraphs starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 5:
        usage ("Not enought arguments!")

    modelName = '';
    fileName = '';
    replaceStr = 'false';
    lastArg = '';
    for arg in sys.argv[1:]:
        if arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "file":
            lastArg="file"
        elif arg.lower() == "replace":
            lastArg="replace"
        elif lastArg == "modelName":
            modelName = arg
            lastArg=''
        elif lastArg == "file":
            fileName = arg
            lastArg=''
        elif lastArg == "replace":
            replaceStr = arg
            lastArg=''
        else:
            usage ("Invalid Argument:" + arg)

    if len(modelName) == 0:
        usage ("Missing required argument MODEL_NAME <modelName>")

    if len(fileName) == 0:
        usage ("Missing required argument FILE <fileName>")

    argList.append("-m")
    argList.append(modelName)

    argList.append("-f")
    argList.append(fileName)

    if replaceStr.lower() == 'true':
        argList.append("-d")

    try:
        logging.info("calling xmImportGraphs with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmImportGraphs", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

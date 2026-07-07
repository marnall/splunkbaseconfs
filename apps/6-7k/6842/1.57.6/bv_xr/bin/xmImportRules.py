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

    usageStatement = "Version 1: xmImportRules MODEL_NAME <modelName> FILE <fileName> [REPLACE (true | false)] [RENAME newPackageName] [VERSION 1]\nVersion 2: xmImportRules FILE <fileName> [REPLACE (true | false)] [RENAME newPackageName]VERSION 2\nREPLACE - if present all rule packages referenced in the import file will be replaced, if not present any rules already present in the database but refernced will be ignored during import."
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmImportRules starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 5:
        usage ("Not enought arguments!")

    modelName = '';
    fileName = '';
    replaceStr = 'false';
    version = '1';
    application = '';
    newName = '';
    lastArg = '';
    for arg in sys.argv[1:]:
        if arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "file":
            lastArg="file"
        elif arg.lower() == "replace":
            lastArg="replace"
        elif arg.lower() == "version":
            lastArg="version"
        elif arg.lower() == "application":
            lastArg="application"
        elif arg.lower() == "rename":
            lastArg="rename"
        elif lastArg == "modelName":
            modelName = arg
            lastArg=''
        elif lastArg == "file":
            fileName = arg
            lastArg=''
        elif lastArg == "replace":
            replaceStr = arg
            lastArg=''
        elif lastArg == "version":
            version = arg
            lastArg=''
        elif lastArg == "application":
            application = arg
            lastArg=''
        elif lastArg == "rename":
            newName = arg
            lastArg=''
        else:
            usage ("Invalid Argument:" + arg)

    if len(fileName) == 0:
        usage ("Missing required argument FILE <fileName>")

    argList.append("--version")
    argList.append(version)

    argList.append("-m")
    argList.append(modelName)

    argList.append("-f")
    argList.append(fileName)

    if len(application) > 0:
        argList.append("-a")
        argList.append(application)

    if len(newName) > 0:
        argList.append("-n")
        argList.append(newName)

    if replaceStr.lower() == 'true':
        argList.append("-d")

    try:
        logging.info("calling xmImportRules with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmImportRules", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

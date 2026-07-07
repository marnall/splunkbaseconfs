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

    usageStatement = "Version 1: xmExportRules MODEL_NAME <modelName> [RULE_PACKAGE <rulePackageName>] [FILE <fileName>] [VERSION 1]\nVersion 2: xmExportRules [RULE_PACKAGE <rulePackageName>] APPLICATION (XVAW | XR | ABA) VERSION 2\nThis command exports the specified rule package to the specified file. If rulePackageName is omitted then all rules defined in the model will be exported. If FILE is omitted rules will be exported to $SPLUNK_HOME/etc/apps/bv_aba/scm/exports/<modelName>_rule-export.csv"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmExportRules starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 3:
        usage ("Not enought arguments!")

    modelName = '';
    fileName = '';
    rulePackageName = '';
    version = '1';
    application = '';
    lastArg = '';
    for arg in sys.argv[1:]:
        if arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "file":
            lastArg="file"
        elif arg.lower() == "rule_package":
            lastArg="rulePackage"
        elif arg.lower() == "version":
            lastArg = "version"
        elif arg.lower() == "application":
            lastArg = "application"
        elif lastArg == "modelName":
            modelName = arg
            lastArg=''
        elif lastArg == "file":
            fileName = arg
            lastArg=''
        elif lastArg == "rulePackage":
            rulePackageName = arg
            lastArg=''
        elif lastArg == "version":
            version = arg
            lastArg=''
        elif lastArg == "application":
            application = arg
            lastArg=''
        else:
            usage ("Invalid Argument:" + arg)

    if version == 1 and len(modelName) == 0:
        usage ("Missing required argument MODEL_NAME <modelName>")

    argList.append("-m")
    argList.append(modelName)

    if len(fileName) > 0:
        argList.append("-f")
        argList.append(fileName)

    if len(rulePackageName) > 0:
        argList.append("-p")
        argList.append(rulePackageName)

    if len(application) > 0:
        argList.append("-a")
        argList.append(application)

    argList.append ("--version");
    argList.append (version);

    try:
        logging.info("calling xmExportRules with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmExportRules", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

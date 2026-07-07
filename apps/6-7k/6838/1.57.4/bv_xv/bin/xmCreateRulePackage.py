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

    usageStatement = "xmCreateRulePackage [MODEL_NAME modelName] RULE_PACKAGE <URLEncodedRulePackageCSV> RULE_SET <URLEncodedRuleSetsCSV> RULES <URLEncodedRules>\n [VERSION (1|2)]";

    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    version = '1'
    modelName = ''
    rulePackage= ''
    ruleSet= ''
    rules= ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmCreateRulePackage starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 7:
            usage ("Incorrect number of arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "model_name":
                lastArg = "modelName";
            elif arg.lower() == "rule_package":
                lastArg="rule_package"
            elif arg.lower() == "rule_set":
                lastArg="rule_set"
            elif arg.lower() == "rules":
                lastArg="rules"
            elif arg.lower() == "version":
                lastArg="version"
            elif lastArg == "modelName":
                modelName = arg
                lastArg = ''
            elif lastArg == "version":
                version = arg
                lastArg = ''
            elif lastArg == "rule_package":
                rulePackage = arg
                lastArg = ''
            elif lastArg == "rule_set":
                ruleSet = arg
                lastArg = ''
            elif lastArg == "rules":
                rules = arg
                lastArg = ''
            else:
                usage ("Invalid Argument:" + arg)

        if len(rulePackage) == 0:
            usage ("Missing argument RULE_PACKAGE <URLEncodedRulePackage>");

        if len(ruleSet) == 0:
            usage ("Missing argument RULE_SET <URLEncodedRulePackage>");

        if len(rules) == 0:
            usage ("Missing argument RULES <URLEncodedRulePackage>");

        if len(modelName) > 0:
            argList.append("-m")
            argList.append (modelName)

        argList.append ("--version");
        argList.append (version);

        argList.append("-p")
        argList.append (rulePackage)

        argList.append("-s"); 
        argList.append(ruleSet); 

        argList.append("-r");
        argList.append(rules);

        logging.info("Calling xmCreateRulePackage with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmCreateRulePackage", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmInstallLicense (FILENAME <licenseFileName> or TRIAL_LICENSE true APPLICATION <appName> or REMOVE <licenseDBId>)\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    lastArg = ''
    fileName = ''
    doTrialLicense = "false"
    applicationName = '' 
    licenseToRemoveId = '' 
    try:
        for arg in sys.argv[1:]:
            if arg.lower() == "filename":
                lastArg="filename"
            elif arg.lower() == "trial_license":
                lastArg="trialLicense"
            elif arg.lower() == "remove":
                lastArg="remove"
            elif arg.lower() == "application":
                lastArg="application"
            elif lastArg == "filename":
                fileName = arg
                lastArg=''
            elif lastArg == "trialLicense":
                doTrialLicense = arg
                lastArg=''
            elif lastArg == "application":
                applicationName=arg
                lastArg=''
            elif lastArg == "remove":
                licenseToRemoveId=arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(fileName) > 0:
            argList.append("-f");
            argList.append(fileName)

        if len(doTrialLicense) > 0 and doTrialLicense.lower() == "true":
            argList.append("-t");

        if len(applicationName) > 0:
            argList.append("-a");
            argList.append(applicationName)

        if len(licenseToRemoveId) > 0:
            argList.append("-r");
            argList.append(licenseToRemoveId)

        logging.info("---------------------------------------------------------------------------------------")
        logging.info("Calling xmInstallLicense with arguments: [" + repr(argList) + "]")

        saUtils.runProcess(sys.argv[0], "xmInstallLicense", argList, False)

        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmImportModel modelName INPUT_FILE_NAME inputFileName [FORCE (true | false)] [VALIDATE_ONLY (true | false)]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    inputFileName= ''
    validateOnly = False
    force = False
    lastArg= ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmImportModel starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 4:
            usage ("Not enought arguments!")

        modelName = sys.argv[1];

        if len(sys.argv) > 2:
            for arg in sys.argv[2:]:
                if arg.lower() == "input_file_name":
                    lastArg="inputFileName"
                elif arg.lower() == "validate_only":
                    lastArg="validateOnly"
                elif arg.lower() == "force":
                    lastArg="force"
                elif lastArg == "inputFileName":
                    inputFileName=arg
                    lastArg=''
                elif lastArg == "validateOnly":
                    temp=arg;
                    if temp.lower() == "true":
                        validateOnly=True
                    else:
                        validateOnly=False
                    lastArg=''
                elif lastArg == "force":
                    temp=arg;
                    if temp.lower() == "true":
                        force=True
                    else:
                        force=False
                    lastArg=''
                else:
                    usage("Unrecognized argument: " + arg)

        argList.append("-m")
        argList.append (modelName)
        
        if len(inputFileName) > 0:
            argList.append("-i")
            argList.append(inputFileName)
        else:
            usage ("missing parameter: INPUT_FILE_NAME <fileName>");

        if validateOnly == True:
            argList.append("-v")

        if force == True:
            argList.append("-f")

        logging.info("Calling xmImportModel with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmImportModel", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

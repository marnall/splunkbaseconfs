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

    usageStatement = "xmExportModel modelName [OUTPUT_FILE_NAME <pathAndFileName>] [PRETTY_OUTPUT (true | false)]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    outputFileName= ''
    prettyOutput=False
    lastArg=''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmExportModel starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")

        modelName = sys.argv[1];

        if len(sys.argv) > 2:
            for arg in sys.argv[2:]:
                if arg.lower() == "output_file_name":
                    lastArg="outputFileName"
                elif arg.lower() == "pretty_output":
                    lastArg="prettyOutput"
                elif lastArg == "outputFileName":
                    outputFileName=arg
                    lastArg=''
                elif lastArg == "prettyOutput":
                    if arg.lower() == "true":
                        prettyOutput = True
                    lastArg=''
                else:
                    usage("Unrecognized argument: " + arg)

        argList.append("-m")
        argList.append (modelName)
        
        if len(outputFileName) > 0:
            argList.append("-o")
            argList.append(outputFileName)

        if prettyOutput == True:
            argList.append("-p")
  
        logging.info("Calling xmExportModel with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmExportModel", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

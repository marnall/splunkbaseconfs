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

    usageStatement = "xmUpdateModel MODEL_NAME modelName PROPS \"prop1=value1|prop2=value2\" DICTIONARY \"dataDef1=field1^_^field2|dataDef2=field3^_^field4^_^field5\"";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    props= ''
    dict= ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmUpdateModel starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 5 or len(sys.argv) > 7:
            usage ("Incorrect number of arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "props":
                lastArg="props"
            elif arg.lower() == "dictionary":
                lastArg="dict"
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "props":
                props = arg
                lastArg=''
            elif lastArg == "dict":
                dict = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(modelName) > 0:
            argList.append("-m");
            argList.append(modelName)
        else:
            usage ("Missing argument MODEL_NAME modelName");

        if len(props) > 0:
            argList.append("-p"); 
            argList.append(props)
        else:
            usage ("Missing argument PROPS propsStr");

        if len(dict) > 0:
            argList.append("-d");
            argList.append(dict)

        logging.info("Calling xmUpdateModel with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmUpdateModel", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

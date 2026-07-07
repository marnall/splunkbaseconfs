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

    usageStatement = "xmListSignalSuppressions [TYPE (default | model | actor)]  [MODEL_NAME modelName] [ACTOR_ID actorId]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListSignalSuppressions starting, args " + repr(sys.argv) + "]");

    modelName= ''
    type= ''
    modelName= ''
    actorId= ''
    lastArg = ''
    try:
        if len(sys.argv) != 1 and len(sys.argv) < 3:
            usage ("Incorrect number of arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "type":
                lastArg="type"
            elif arg.lower() == "model_name":
                lastArg="modelName" 
            elif arg.lower() == "actor_id":
                lastArg="actorId"
            elif lastArg == "type":
                type = arg
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "actorId":
                actorId = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(type) > 0:
            if type.lower() != "default" and type.lower() != "model" and type.lower() != "actor" and type.lower() != "taxonomy":
                usage ("Invalid type: [" + type + "] received!")
            argList.append("-t")
            argList.append (type)

        if len(modelName) > 0:
            argList.append("-m")
            argList.append (modelName)

        if len(actorId) > 0:
            argList.append("-a")
            argList.append (actorId)

        logging.info("Calling xmListSignalSuppressions with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListSignalSuppressions", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

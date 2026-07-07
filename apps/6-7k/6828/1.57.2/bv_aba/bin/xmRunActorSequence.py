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

    usageStatement = "xmRunActorSequence modelName [ANALYSISNAME name] [ACTORID actorId] [STARTDATE mm/dd/yyyy] [TESTONLY true||false] [SIGNALPROPS \"prop1=value1|prop2=value2\" ]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    testOnly = ''
    modelName = ''
    analysisName = ''
    removeTerrains = ''
    signalProps= ''
    actorId = ''
    startDate = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRunActorSequence starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 2:
            usage ("Not enought arguments!")

        modelName = sys.argv[1];

        for arg in sys.argv[2:]:
            if arg.lower() == "actorid":
                lastArg="actorid"
            elif arg.lower() == "startdate":
                lastArg="startdate"
            elif arg.lower() == "removeterrains":
                lastArg="removeterrains"
            elif arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif arg.lower() == "testonly":
                lastArg="testonly"
            elif lastArg == "actorid":
                actorId = arg
                lastArg=''
            elif lastArg == "startdate":
                startDate = arg
                lastArg=''
            elif lastArg == "removeterrains":
                removeTerrains = arg
            elif lastArg == "analysisname":
                analysisName = arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps = arg
                lastArg=''
            elif lastArg == "testonly":
                testOnly = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        argList.append("-m"); 
        argList.append(modelName);

        if len(actorId) > 0:
            argList.append("-a")
            argList.append (actorId)
            
        if len(startDate) > 0:
            argList.append("-t"); 
            argList.append(startDate)

        if len(removeTerrains) > 0:
            argList.append("-r");
            argList.append(removeTerrains);

        if len(analysisName) > 0:
            argList.append("-n"); 
            argList.append(analysisName)

        if len(signalProps) > 0:
            argList.append("-p"); 
            argList.append(signalProps)

        if len(testOnly) > 0:
            argList.append ("-T")
            argList.append (testOnly)

        logging.info("Calling xmRunActorSequence with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRunActorSequence", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

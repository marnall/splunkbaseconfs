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

    usageStatement = "xmListActorSequence MODELNAME actorId [INCLUDE_EVENT_TIMES]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    actorId = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListActorSequence starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 3:
            usage ("Not enought arguments!")

        modelName = sys.argv[1];
        actorId = sys.argv[2];

        argList.append("-m")
        argList.append (modelName)
        argList.append("-a")
        argList.append (actorId)

        if len(sys.argv) == 4:
            if sys.argv[3].lower().startswith ("include_event_times"):
                argList.append ("-t");
            else:
                usage ("Invalid argument: " + sys.argv[3]);

        logging.info("Calling xmListActorSequence with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListActorSequence", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

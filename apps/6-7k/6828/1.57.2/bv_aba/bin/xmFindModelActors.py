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

    usageStatement = "xmFindModelActors modelName searchString\nsearchString - first N characters of actors to find.\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    searchString = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmFindModelActors starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) != 3:
            usage ("Incorrect number of arguments!")

        modelName = sys.argv[1];
        argList.append("-m")
        argList.append (modelName)

        searchString = sys.argv[2];
        argList.append("-s")
        argList.append (searchString)

        logging.info("Calling xmFindModelActors with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmFindModelActors", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

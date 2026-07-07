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

    usageStatement = "xmRemoveFuzzyCluster CLUSTER_NAME name";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    clusterName = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRemoveFuzzyCluster starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 3:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "cluster_name":
                lastArg="clusterName"
            elif lastArg == "clusterName":
                clusterName = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(clusterName) > 0:
            argList.append("-n"); 
            argList.append(clusterName)
        else:
            usage ("Missing argument CLUSTER_NAME name");

        logging.info("Calling xmRemoveFuzzyCluster with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRemoveFuzzyCluster", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmListGraphs GRAPH_TYPE graphType";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    graphType = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmListGraphs starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 3:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "graph_type":
                lastArg="graphType"
            elif lastArg == "graphType":
                graphType = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(graphType) > 0:
            argList.append("-g"); 
            argList.append(graphType)
        else:
            usage ("Missing argument GRAPH_TYPE graphType");

        logging.info("Calling xmListGraphs with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmListGraphs", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

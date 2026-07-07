# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to extract events that fall into a specified time period 
# of a certain taxonomy from an actors landscape model. 
#
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
        logging.error (message);

    usageStatement = "xmExportGraphs GRAPH_TYPE (RELEVANCY | TRANSACTION) MODEL_NAME <modelName> [GRAPH_NAME <rulePackageName>] [FILE <fileName>]\nThis command exports the specified graphs to the specified file. If graphName is omitted then all graphs of the specified type from the model will be exported. If FILE is omitted rules will be exported to $SPLUNK_HOME/etc/apps/bv_xv/scm/exports/<modelName>_graph-export.json"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmExportGraphs starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 3:
        usage ("Not enought arguments!")

    graphType = '';
    modelName = '';
    fileName = '';
    graphName = '';
    lastArg = '';
    for arg in sys.argv[1:]:
        if arg.lower() == "graph_type":
            lastArg="graphType"
        elif arg.lower() == "model_name":
            lastArg="modelName"
        elif arg.lower() == "file":
            lastArg="file"
        elif arg.lower() == "graph_name":
            lastArg="graphName"
        elif lastArg == "graphType":
            graphType = arg
            lastArg=''
        elif lastArg == "modelName":
            modelName = arg
            lastArg=''
        elif lastArg == "file":
            fileName = arg
            lastArg=''
        elif lastArg == "graphName":
            rulePackageName = arg
            lastArg=''
        else:
            usage ("Invalid Argument:" + arg)

    if len(graphType) == 0:
        usage ("Missing required argument GRAPH_TYPE <type>")

    if len(modelName) == 0:
        usage ("Missing required argument MODEL_NAME <modelName>")

    argList.append("-t")
    argList.append(graphType)

    argList.append("-m")
    argList.append(modelName)

    if len(fileName) > 0:
        argList.append("-f")
        argList.append(fileName)

    if len(graphName) > 0:
        argList.append("-n")
        argList.append(graphName)

    try:
        logging.info("calling xmExportGraphs with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmExportGraphs", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

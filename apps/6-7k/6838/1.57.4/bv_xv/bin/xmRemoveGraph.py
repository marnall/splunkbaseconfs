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

    usageStatement = "xmRemoveGraph GRAPH_TYPE graphType GRAPH_NAME graphName [MODEL_NAME modelName] [RECURSIVE (true | false)]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    graphType = ''
    grapName = ''
    modelName = ''
    recursive = 'false'
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRemoveGraph starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 5:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "graph_type":
                lastArg="graphType"
            elif arg.lower() == "graph_name":
                lastArg="graphName"
            elif arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "recursive":
                lastArg="recursive"
            elif lastArg == "graphType":
                graphType = arg
                lastArg=''
            elif lastArg == "graphName":
                graphName = arg
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "recursive":
                recursive = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(graphType) > 0:
            argList.append("-g"); 
            argList.append(graphType)
        else:
            usage ("Missing argument GRAPH_TYPE graphType");

        if len(graphName) > 0:
            argList.append("-N"); 
            argList.append(graphName)
        else:
            usage ("Missing argument GRAPH_NAME graphName");

        if len(modelName) > 0:
            argList.append("-m");
            argList.append(modelName)

        argList.append("-R");
        argList.append(recursive)
    
        logging.info("Calling xmRemoveGraph with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRemoveGraph", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmUpdateGraph (GRAPH_ID graphId | GRAPH_TYPE graphType GRAPH_NAME graphName MODEL_NAME moodelName) [NEW_GRAPH_NAME newName] [GRAPH_PROPS \"prop1=value1|prop2=value2\"]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    graphType = ''
    graphName = ''
    newGraphName = ''
    graphId = ''
    modelName = ''
    graphProps = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmUpdateGraph starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 5:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "graph_type":
                lastArg="graphType"
            elif arg.lower() == "graph_id":
                lastArg="graphId"
            elif arg.lower() == "graph_name":
                lastArg="graphName"
            elif arg.lower() == "new_graph_name":
                lastArg="newGraphName"
            elif arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "graph_props":
                lastArg="graphProps"
            elif lastArg == "graphType":
                graphType = arg
                lastArg=''
            elif lastArg == "graphId":
                graphId = arg
                lastArg=''
            elif lastArg == "graphName":
                graphName = arg
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "newGraphName":
                newGraphName = arg
                lastArg=''
            elif lastArg == "graphProps":
                graphProps = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(graphId) > 0:
            argList.append("-i");
            argList.append(graphId)
        else:
            if len(graphName) > 0:
                argList.append("-N");
                argList.append(graphName)
            else:
                usage ("Missing argument GRAPH_NAME graphName");

            if len(modelName) > 0:
                argList.append("-m");
                argList.append(modelName)
            else:
                usage ("Missing argument MODEL_NAME modelName");

            if len(graphType) > 0:
                argList.append("-g");
                argList.append(graphType)
            else:
                usage ("Missing argument GRAPH_TYPE graphType");

        # Make sure newGraphName and/or graphProps have been specified.
        if len(newGraphName) == 0 and len(graphProps) == 0:
            usage ("NEW_GRAPH_NAME newName and/or GRAPH_PROPS graphProperties MUST be specified") 

        if len(newGraphName) > 0:
            argList.append("-n"); 
            argList.append(newGraphName)

        if len(graphProps) > 0:
            argList.append("-p"); 
            argList.append(graphProps)

        logging.info("Calling xmUpdateGraph with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmUpdateGraph", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

splunkHome=os.environ.get('SPLUNK_HOME')

def usage(message):

    if len (message) > 0:
        sys.stderr.write (message + "\n");

    usageStatement = "xmAddGraphEdge GRAPH_TYPE graphType GRAPH_NAME graphName EDGE_NAME edgeName FROM_NODE_NAME nodeName TO_NODE_NAME [MODEL_NAME moodelName] [EDGE_PROPS \"prop1=value1|prop2=value2\" ]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    graphType = ''
    grapName = ''
    modelName = '' 
    edgeName = ''
    fromNodeName = ''
    toNodeName = ''
    edgeProps = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmAddGraphEdge starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 8:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "graph_type":
                lastArg="graphType"
            elif arg.lower() == "graph_name":
                lastArg="graphName"
            elif arg.lower() == "edge_name":
                lastArg="edgeName"
            elif arg.lower() == "from_node_name":
                lastArg="fromNodeName"
            elif arg.lower() == "to_node_name":
                lastArg="toNodeName"
            elif arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "edge_props":
                lastArg="edgeProps"
            elif lastArg == "graphType":
                graphType = arg
                lastArg=''
            elif lastArg == "graphName":
                graphName = arg
                lastArg=''
            elif lastArg == "edgeName":
                edgeName = arg
                lastArg=''
            elif lastArg == "fromNodeName":
                fromNodeName = arg
                lastArg=''
            elif lastArg == "toNodeName":
                toNodeName = arg
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg 
                lastArg=''
            elif lastArg == "edgeProps":
                edgeProps = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(graphType) > 0:
            argList.append("-g")
            argList.append(graphType)
        else:
            usage ("Missing argument GRAPH_TYPE graphType");

        if len(graphName) > 0:
            argList.append("-N")
            argList.append(graphName)
        else:
            usage ("Missing argument GRAPH_NAME graphName");
    
        if len(fromNodeName) > 0:
            argList.append("-f")
            argList.append(fromNodeName)
        else:
            usage ("Missing argument FROM_NODE_NAME nodeName");

        if len(toNodeName) > 0:
            argList.append("-t")
            argList.append(toNodeName)
        else:
            usage ("Missing argument TO_NODE_NAME nodeName");

        if len(edgeName) > 0:
            argList.append("-n")
            argList.append(edgeName)

        if len(modelName) > 0:
            argList.append("-m");
            argList.append(modelName)

        if len(edgeProps) > 0:
            argList.append("-p")
            argList.append(edgeProps)

        logging.info("Calling xmAddGraphEdge with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmAddGraphEdge", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

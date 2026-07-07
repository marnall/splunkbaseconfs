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

    usageStatement = "xmAddGraphNode GRAPH_TYPE graphType GRAPH_NAME graphName NODE_NAME nodeName IS_ROOT (true | false) [MODEL_NAME moodelName] [GRAPH_PROPS \"prop1=value1|prop2=value2\" ] [NODE_PROPS \"prop1=value1|prop2=value2\" ]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    graphType = ''
    grapName = ''
    modelName = ''
    nodeName = ''
    isRoot = ''
    graphProps = ''
    nodeProps = ''
    lastArg= ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmAddGraphNode starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 8:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "graph_type":
                lastArg="graphType"
            elif arg.lower() == "graph_name":
                lastArg="graphName"
            elif arg.lower() == "node_name":
                lastArg="nodeName"
            elif arg.lower() == "is_root":
                lastArg="isRoot"
            elif arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "graph_props":
                lastArg="graphProps"
            elif arg.lower() == "node_props":
                lastArg="nodeProps"
            elif lastArg == "graphType":
                graphType = arg
                lastArg=''
            elif lastArg == "graphName":
                graphName = arg
                lastArg=''
            elif lastArg == "nodeName":
                nodeName = arg
                lastArg=''
            elif lastArg == "isRoot":
                isRoot = arg
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "graphProps":
                graphProps = arg
                lastArg=''
            elif lastArg == "nodeProps":
                nodeProps = arg
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
    
        if len(nodeName) > 0:
            argList.append("-n"); 
            argList.append(nodeName)
        else:
            usage ("Missing argument NODE_NAME nodeName");

        if len(isRoot) > 0:
            argList.append("-r");
            argList.append(isRoot)
        else:
            usage ("Missing argument IS_ROOT (true | false)");

        if len(modelName) > 0:
            argList.append("-m"); 
            argList.append(modelName)

        if len(graphProps) > 0:
            argList.append("-p"); 
            argList.append(graphProps)

        if len(nodeProps) > 0:
            argList.append("-P"); 
            argList.append(nodeProps)

        logging.info("Calling xmAddGraphNode with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmAddGraphNode", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

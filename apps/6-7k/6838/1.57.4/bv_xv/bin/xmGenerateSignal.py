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

    usageStatement = "xmGenerateSignal [APPLICATION <app>] [SIGNAL_TYPE <signalType>] [ID signalId] [MODEL <modelName>] [CATEGORY <INFORMATION | ANOMALY | AD_HOC>] [ANALYSIS_NAME <name>] [ACTOR_ID <actorId>] [ACTION <action>] [PROCESS <process>] [FIELD <field>] [INTENSITY <decimal>] [WEIGHT <weight>] [PROPS \"prop1=value1|prop2=value2|...\"]";

    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    application = ''
    signalType = ''
    id = ''
    model = ''
    category = ''
    analysisName = ''
    actorId = ''
    action = ''
    process = ''
    field = ''
    intensity = ''
    weight = ''
    props = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmGenerateSignal starting, args " + repr(sys.argv) + "]");

    try:

        for arg in sys.argv[1:]:
            if arg.lower() == "application":
                lastArg="application"
            elif arg.lower() == "signal_type":
                lastArg="signalType"
            elif arg.lower() == "id":
                lastArg="id"
            elif arg.lower() == "model":
                lastArg="model"
            elif arg.lower() == "category":
                lastArg="category"
            elif arg.lower() == "analysis_name":
                lastArg="analysisName"
            elif arg.lower() == "intensity":
                lastArg="intensity"
            elif arg.lower() == "weight":
                lastArg="weight"
            elif arg.lower() == "actor_id":
                lastArg="actorId"
            elif arg.lower() == "action":
                lastArg="action"
            elif arg.lower() == "process":
                lastArg="process"
            elif arg.lower() == "field":
                lastArg="field"
            elif arg.lower() == "props":
                lastArg="props"
            elif lastArg == "application":
                application = arg
                lastArg=''
            elif lastArg == "signalType":
                signalType = arg
                lastArg=''
            elif lastArg == "id":
                id = arg
                lastArg=''
            elif lastArg == "model":
                model = arg
                lastArg=''
            elif lastArg == "category":
                category = arg
                lastArg=''
            elif lastArg == "analysisName":
                analysisName = arg
                lastArg=''
            elif lastArg == "actorId":
                actorId = arg
                lastArg=''
            elif lastArg == "action":
                action = arg
                lastArg=''
            elif lastArg == "process":
                process = arg
                lastArg=''
            elif lastArg == "field":
                field = arg
                lastArg=''
            elif lastArg == "intensity":
                intensity = arg
                lastArg=''
            elif lastArg == "weight":
                weight = arg
                lastArg=''
            elif lastArg == "props":
                props = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(id) > 0:
            argList.append("-I")
            argList.append(id)

        if len(signalType) > 0:
            argList.append("-t")
            argList.append(signalType)
    
        if len(application) > 0:
            argList.append("-A")
            argList.append(application)

        if len(model) > 0:
            argList.append("-m")
            argList.append(model)

        if len(category) > 0:
            argList.append("-c")
            argList.append(category)

        if len(analysisName) > 0:
            argList.append("-a")
            argList.append (analysisName);

        if len(actorId) > 0:
            argList.append("-d")
            argList.append (actorId);

        if len(action) > 0:
            argList.append("-T")
            argList.append (action)

        if len(process) > 0:
            argList.append("-P")
            argList.append (process)

        if len(field) > 0:
            argList.append("-f")
            argList.append (field)

        if len(intensity) > 0:
            argList.append("-i")
            argList.append (intensity)

        if len(weight) > 0:
            argList.append("-w")
            argList.append (weight)

        if len(props) > 0:
            argList.append("-p")
            argList.append (props)

        logging.info("Calling xmGenerateSignal with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmGenerateSignal", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

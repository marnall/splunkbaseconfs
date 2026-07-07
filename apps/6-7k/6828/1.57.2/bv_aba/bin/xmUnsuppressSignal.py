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

    usageStatement = "xmUnsuppressSignal modelName TYPE (model | actor | taxonomy) SIGNAL_TYPE signalType [ACTOR_ID <actorId>] [TAXONOMY_ID [Actor~][Action~process~field]] [PARTIAL_TAXONOMY_ID <taxonomyRegEx>] [PROPERTY_NAME <propertyName> PROPERTY_VALUE <propertyValue>]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName= ''
    type= ''
    signalType= ''
    actorId = ''
    taxonomyId = ''
    partialTaxonomyId = ''
    propertyName = ''
    propertyValue = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmUnsuppressSignal starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) < 4:
            usage ("Not enought arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "type":
                lastArg="type"
            elif arg.lower() == "signal_type":
                lastArg="signalType"
            elif arg.lower() == "actor_id":
                lastArg="actorId"
            elif arg.lower() == "property_name":
                lastArg="propertyName"
            elif arg.lower() == "property_value":
                lastArg="propertyValue"
            elif arg.lower() == "taxonomy_id":
                lastArg="taxonomyId"
            elif arg.lower() == "partial_taxonomy_id":
                lastArg="partialTaxonomyId"
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "type":
                type = arg
                lastArg=''
            elif lastArg == "signalType":
                signalType = arg
                lastArg=''
            elif lastArg == "actorId":
                actorId = arg
                lastArg=''
            elif lastArg == "taxonomyId":
                taxonomyId = arg
                lastArg=''
            elif lastArg == "partialTaxonomyId":
                partialTaxonomyId = arg
                lastArg=''
            elif lastArg == "propertyName":
                propertyName = arg
                lastArg=''
            elif lastArg == "propertyValue":
                propertyValue = arg
                lastArg=''
            else:
                usage ("Invalid Argument: " + arg)

        if len(type) > 0:
            argList.append("-t"); 
            argList.append(type)
        else:
            usage ("Missing argument TYPE (default | model | actor | taxonomy)");

        if len(signalType) > 0:
            argList.append("-s"); 
            argList.append(signalType)
        elif type.lower() != "default":
            usage ("Missing argument SIGNAL_TYPE <signalType>");

        if type.lower() != "default" and type.lower() != "model" and type.lower() != "actor" and type.lower() != "taxonomy":
            usage ("Invalid type: [" + type.lower() + "], valid types are: (default | model | actor | taxonomy)");

        if type.lower() == "default" and len(signalType) == 0 and len(partialTaxonomyId) == 0:
            usage ("Missing argument SIGNAL_TYPE <signalType> and/or PARTIAL_TAXONOMY_ID <regExTaxonomyId>")
        elif ((type.lower() == "model" or type.lower() == "actor" or type.lower() == "taxonomy") and len(modelName) == 0):
            usage ("Missing argument MODEL_NAME <modelName>")
        elif type.lower() == "actor" and len(actorId) == 0:
            usage ("Missing argument ACTOR_ID <actorId>")
        elif type.lower() == "taxonomy" and len(taxonomyId) == 0:
            if len(propertyName) == 0 or len(propertyValue) == 0:
                usage ("Missing arguments [TAXONOMY_ID <taxonomyId>] or [PROPERTY_NAME <propertyName> PROPERTY_VALUE <propertyValue>]")

        if len(modelName) > 0:
            argList.append ("-m");
            argList.append (modelName);
    
        if len(actorId) > 0:
            argList.append("-a"); 
            argList.append(actorId)

        if len(taxonomyId) > 0:
            argList.append("-T");
            argList.append(taxonomyId)

        if len(partialTaxonomyId) > 0:
            argList.append("-r");
            argList.append(partialTaxonomyId)

        if len(propertyName) > 0:
            argList.append("-p");
            argList.append(propertyName)

        if len(propertyValue) > 0:
            argList.append("-P");
            argList.append(propertyValue)

        logging.info("Calling xmUnsuppressSignal with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmUnsuppressSignal", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

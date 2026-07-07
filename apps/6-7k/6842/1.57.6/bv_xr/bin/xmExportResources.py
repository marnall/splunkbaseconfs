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

    usageStatement = "xmExportResources [ACTORS_ASSETS (true | false)] [CONFIG (true|false)] [ALL (true | false)] [ACTORS (true | false)] [ASSETS (true | false)] [DATA_DICTIONARY (true | false)] [PROPERTIES (true | false)] [MAPPINGS (true | false)] [OUTPUT_FILE_NAME fileName] [PARAMS \"param1,param2,param3\"]\nThis command will export actors, assets, data-dictionary, resource-mappings, and properties from the database to the default file they are loaded from. If no parameters are provided then all resources will be exported to their appropriate output file in the lookups directory.\nOUTPUT_FILE_NAME fileName is valid with DATA_DICTIONARY true to specify the name and location of the export data_dictionary file.\nPARAMS \"param1,param2,param3\" is valid with DATA_DICTIONARY true is used to specify the names of data definitions to export";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    lastArg = ''
    exportActors = 'false'
    exportAssets = 'false'
    exportProperties = 'false'
    exportDataDictionary = 'false'
    exportMappings = 'false'
    exportFileName = ''
    exportParams = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmExportResources starting, args " + repr(sys.argv) + "]");

    try:

        for arg in sys.argv[1:]:
            if arg.lower() == "actors_assets":
                lastArg="actors_assets"
            elif arg.lower() == "config":
                lastArg="config"
            elif arg.lower() == "all":
                lastArg="all"
            elif arg.lower() == "actors":
                lastArg="actors"
            elif arg.lower() == "assets":
                lastArg="assets"
            elif arg.lower() == "data_dictionary":
                lastArg="data_dictionary"
            elif arg.lower() == "properties":
                lastArg="properties"
            elif arg.lower() == "mappings":
                lastArg="mappings"
            elif arg.lower() == "output_file_name":
                lastArg="outputFile"
            elif arg.lower() == "params":
                lastArg="params"
            elif lastArg == "actors_assets":
                exportActors = 'true'
                exportAssets = 'true'
                lastArg=''
            elif lastArg == "config":
                exportProperties = 'true'
                exportDataDictionary = 'true'
                exportMappings = 'true'
                lastArg=''
            elif lastArg == "all":
                exportActors = 'true'
                exportAssets = 'true'
                exportProperties = 'true'
                exportDataDictionary = 'true'
                exportMappings = 'true'
                lastArg=''
            elif lastArg == "actors":
                exportActors = arg
                lastArg=''
            elif lastArg == "assets":
                exportAssets = arg
                lastArg=''
            elif lastArg == "data_dictionary":
                exportDataDictionary = arg
                lastArg=''
            elif lastArg == "properties":
                exportProperties = arg
                lastArg=''
            elif lastArg == "mappings":
                exportMappings = arg
                lastArg=''
            elif lastArg == "outputFile":
                exportFileName = arg
                lastArg=''
            elif lastArg == "params":
                exportParams = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        # No arguments then export all
        if (len(sys.argv) == 1 or
           (exportActors == 'false' and exportAssets == 'false'
            and exportProperties == 'false' and exportDataDictionary == 'false'
            and exportMappings == 'false')):

            exportActors = 'true'
            exportAssets = 'true'
            exportProperties = 'true'
            exportDataDictionary = 'true'
            exportMappings = 'true'

        argList.append ("-a");
        argList.append (exportActors);

        argList.append ("-A");
        argList.append (exportAssets);

        argList.append ("-d");
        argList.append (exportDataDictionary);

        argList.append ("-p");
        argList.append (exportProperties);

        argList.append ("-m");
        argList.append (exportMappings);

        if len(exportFileName) > 0:
            argList.append ("-f");
            argList.append (exportFileName);

        if len(exportParams) > 0:
            argList.append ("-P");
            argList.append (exportParams);

        logging.info("Calling xmExportResources with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmExportResources", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

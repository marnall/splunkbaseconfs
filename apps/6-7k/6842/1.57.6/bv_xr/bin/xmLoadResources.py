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

    usageStatement = "xmLoadResources [ACTORS_ASSETS (true | false)] [CONFIG (true|false)] [ALL (true | false)] [ACTORS (true | false)] [ASSETS (true | false)] [DATA_DICTIONARY (true | false)] [PROPERTIES (true | false)] [MAPPINGS (true | false)] [FORCE (true | false)] [APPEND (true)] FILE <fileName>] [REMOVEINPUT (true | false)]\nThis command will load actors, assets, data-dictionary, resource-mappings, and properties if they are not already loaded. Use FORCE true force load of the specified resources (delete then load). If no parameters are provided then all resources will be loaded if they don't exist in the datastore. The append option can be used to append data dictionary, actors, assets, and resource mappings to existing entries in the data store. Here is an example that shows how to use append\nxmLoadResources DATA_DICTIONARY true APPEND true FILE /tmp/data-dictionary.json or xmLoadResources ACTORS true APPEND true FILE /tmp/data-dictionary.json FORCE true. The REMOVEINPUT parameter is valid when FILE is specified to have input file removed after successful import.";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    lastArg = ''
    loadActors = 'false'
    loadAssets = 'false'
    loadProperties = 'false'
    loadDataDictionary = 'false'
    loadMappings = 'false'
    force = 'false'
    append = 'false'
    removeInput = ''
    file = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmLoadResources starting, args " + repr(sys.argv) + "]");

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
            elif arg.lower() == "force":
                lastArg="force"
            elif arg.lower() == "append":
                lastArg="append"
            elif arg.lower() == "file":
                lastArg="file"
            elif arg.lower() == "removeinput":
                lastArg="removeInput"
            elif lastArg == "actors_assets":
                loadActors = 'true'
                loadAssets = 'true'
                lastArg=''
            elif lastArg == "config":
                loadProperties = 'true'
                loadDataDictionary = 'true'
                loadMappings = 'true'
                lastArg=''
            elif lastArg == "all":
                loadActors = 'true'
                loadAssets = 'true'
                loadProperties = 'true'
                loadDataDictionary = 'true'
                loadMappings = 'true'
                lastArg=''
            elif lastArg == "force":
                force = arg
                lastArg=''
            elif lastArg == "actors":
                loadActors = arg
                lastArg=''
            elif lastArg == "assets":
                loadAssets = arg
                lastArg=''
            elif lastArg == "data_dictionary":
                loadDataDictionary = arg
                lastArg=''
            elif lastArg == "properties":
                loadProperties = arg
                lastArg=''
            elif lastArg == "mappings":
                loadMappings = arg
                lastArg=''
            elif lastArg == "append":
                append = arg
                lastArg=''
            elif lastArg == "file":
                file = arg
                lastArg=''
            elif lastArg == "removeInput":
                removeInput = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        # No arguments or force true, load all
        if (len(sys.argv) == 1 or
           (force == 'true' and loadActors == 'false' and loadAssets == 'false'
            and loadProperties == 'false' and loadDataDictionary == 'false'
            and loadMappings == 'false' and append == 'false')):

            loadActors = 'true'
            loadAssets = 'true'
            loadProperties = 'true'
            loadDataDictionary = 'true'
            loadMappings = 'true'

        # Validate append arguments.
        if append == 'true':
            # Count the number of options specified.
            numOptionsSelected = 0
            if loadActors == 'true':
                numOptionsSelected = numOptionsSelected+1;
            if loadAssets == 'true':
                numOptionsSelected = numOptionsSelected+1;
            if loadProperties == 'true':
                numOptionsSelected = numOptionsSelected+1;
            if loadDataDictionary == 'true':
                numOptionsSelected = numOptionsSelected+1;
            if loadMappings == 'true':
                numOptionsSelected = numOptionsSelected+1;

            if file == '':
                usage ("FILE <fileName> must be specified when using the append option");
            elif numOptionsSelected == 0:
                usage ("One of the following is required when USING append: DATA_DICTIONARY true OR ACTORS true OR ASSETS true OR PROPERTIES true OR MAPPINGS true");
            elif numOptionsSelected != 1:
                usage ("Only one of the following can be specified when using APPEND: DATA_DICTIONARY true OR ACTORS true OR ASSETS true OR PROPERTIES true OR MAPPINGS true");

        argList.append ("-a");
        argList.append (loadActors);

        argList.append ("-A");
        argList.append (loadAssets);

        argList.append ("-d");
        argList.append (loadDataDictionary);

        argList.append ("-p");
        argList.append (loadProperties);

        argList.append ("-m");
        argList.append (loadMappings);

        argList.append ("-f");
        argList.append (force);

        argList.append ("-P");
        argList.append (append);

        if file != '':
            argList.append ("-F")
            argList.append (file)

            # Remove input only valid when FILE is specified.
            if len (removeInput) > 0:
                argList.append ("-r")
                argList.append (removeInput)

        logging.info("Calling xmLoadResources with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmLoadResources", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

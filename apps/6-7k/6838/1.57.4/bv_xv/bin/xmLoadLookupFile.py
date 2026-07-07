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

    usageStatement = "xmLoadLookupFile COLLECTION collectionName INDEX_COLUMNN nameOfColumnToIndex FILE lookupCSVFileToLoad [CLEAR (true | false)]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    collection=''
    indexColumn=''
    file=''
    clear='false'
    lastArg=''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmLoadLookupFile starting, args " + repr(sys.argv) + "]");

    if len(sys.argv) < 5:
        usage ("Incorrect number of args!");

    for arg in sys.argv[1:]:
        if arg.lower() == "collection":
            lastArg="collection"
        elif arg.lower() == "index_column":
            lastArg="index_column"
        elif arg.lower() == "file":
            lastArg="file"
        elif arg.lower() == "clear":
            lastArg="clear"
        elif lastArg == "collection":
            collection=arg
            lastArg=''
        elif lastArg == "index_column":
            indexColumn=arg
            lastArg=''
        elif lastArg == "file":
            file=arg
            lastArg=''
        elif lastArg == "clear":
            clear=arg
            lastArg=''
        else:
            usage("Unrecognized argument: " + arg)

    if len (collection) == 0:
        usage ("Missing argument COLLECTION collectionName");

    if len (indexColumn) == 0:
        usage ("Missing argument INDEX_COLUMN nameOfColumnToIndex");

    if len (file) == 0:
        usage ("Missing argument FILE lookupCSVFileToLoad");

    argList.append ("-c");
    argList.append (collection);

    argList.append ("-i");
    argList.append (indexColumn);

    argList.append ("-f");
    argList.append (file);

    argList.append ("-C");
    argList.append (clear);

    try:
        logging.info("Calling xmLoadLookupFile with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmLoadLookupFile", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

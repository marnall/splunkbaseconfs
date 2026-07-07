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

    usageStatement = "xmRemoveTransactionSequence TRANSACTION_NAME transactionName [MODEL_NAME modelName] [SEQUENCE_NAME sequenceName]";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    transactionName = ''
    sequenceName= ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmRemoveTransactionSequence starting, args " + repr(sys.argv) + "]");

    try:
        if len(sys.argv) > 7:
            usage ("Too many arguments!")

        for arg in sys.argv[1:]:
            if arg.lower() == "model_name":
                lastArg="modelName"
            elif arg.lower() == "transaction_name":
                lastArg="transaction_name"
            elif arg.lower() == "sequence_name":
                lastArg="sequence_name"
            elif arg.lower() == "name":
                lastArg="name"
                lastArg=''
            elif lastArg == "modelName":
                modelName = arg
                lastArg=''
            elif lastArg == "transaction_name":
                transactionName = arg
                lastArg=''
            elif lastArg == "sequence_name":
                sequenceName = arg
                lastArg=''
            else:
                usage ("Invalid Argument:" + arg)

        if len(transactionName) > 0:
            argList.append("-t");
            argList.append(transactionName)
        else:
            usage ("Missing parameter TRANSACTION_NAME name");

        if len(modelName) > 0:
            argList.append("-m");
            argList.append(modelName)

        if len(sequenceName) > 0:
            argList.append("-n");
            argList.append(sequenceName)

        logging.info("Calling xmRemoveTransactionSequence with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmRemoveTransactionSequence", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

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

    usageStatement = "xmActivateModel modelName [DENSITY (true | false)] [THRESHOLDS (true | false)] [THRESHOLD_TYPE (aggregate | day_of_week)] [NUM_THRESHOLD_TIME_PERIODS (1 | 2 | 4 | 6| 8 | 24)]\n";
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    modelName = ''
    doDensity= 'true'
    doThresholds = 'true'
    thresholdType = ''
    numThresholdTimePeriods = ''
    lastArg = ''
    logging.info("---------------------------------------------------------------------------------------")
    logging.info("xmActivateModel starting, args " + repr(sys.argv) + "]");

    try:

        modelName = sys.argv[1];

        if len(sys.argv) > 2:
            for arg in sys.argv[2:]:
                if arg.lower() == "density":
                    lastArg="density"
                elif arg.lower() == "thresholds":
                    lastArg="thresholds"
                elif arg.lower() == "threshold_type":
                    lastArg="thresholdType"
                elif arg.lower() == "num_threshold_time_periods":
                    lastArg="numTimePeriods"
                elif lastArg == "density":
                    doDensity=arg
                    lastArg=''
                elif lastArg == "thresholds":
                    doThresholds=arg
                    lastArg=''
                elif lastArg == "thresholdType":
                    thresholdType=arg
                    lastArg=''
                elif lastArg == "numTimePeriods":
                    numThresholdTimePeriods=arg
                    lastArg=''
                else:
                    usage("Unrecognized argument: " + arg)

        argList.append("-m")
        argList.append (modelName)

        if len(doDensity) > 0:
            argList.append("-i")
            argList.append(doDensity)

        if len(doThresholds) > 0:
            argList.append("-t")
            argList.append(doThresholds)

        if len(thresholdType) > 0:
            if thresholdType.lower() != "aggregate" and thresholdType.lower() != "day_of_week":
                 usage ("Invalid threshold type: " + thresholdType + ", valid values are day_of_week OR aggregate");
            else:
                argList.append("-T");
                argList.append(thresholdType);

        if len(numThresholdTimePeriods) > 0:
            argList.append("-p")
            argList.append(numThresholdTimePeriods)

        logging.info("Calling xmActivateModel with arguments: [" + repr(argList) + "]")
        saUtils.runProcess(sys.argv[0], "xmActivateModel", argList, False)
        logging.info("---------------------------------------------------------------------------------------")

    except Exception as e:
        si.generateErrorResults(e)

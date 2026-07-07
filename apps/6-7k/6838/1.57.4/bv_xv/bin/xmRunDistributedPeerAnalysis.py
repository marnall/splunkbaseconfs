# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
#
# This command is used to run peer to peer actor analsysis.
#
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
        logging.error (message);

    usageStatement = "xmRunDistributedPeerAnalysis modelName [ANALYSISNAME name] [REGION regionName] [BUSINESSUNIT businessUnitName] [TITLE titleName] [CATEGORY categoryName] [MANAGEDBY managerName] [STARTDATE mm/dd/yyyy] [ACTORTYPE HUMAN (default) or MACHINE or SERVICE] [TAG tag]"
    logging.error (usageStatement)
    sys.stderr.write (usageStatement);
    raise Exception (usageStatement);

if __name__ == '__main__':

    argList = []
    logging.info ("-------------------------------------------------------------------------------------")
    logging.info("xmRunDistributedPeerAnalysis starting, args [" + repr(sys.argv) + "]");

    if len(sys.argv) < 2:
        usage ("Not enought arguments!")

    lastArg='';
    analysisName='';
    signalProps='';
    region='';
    businessunit='';
    title='';
    category='';
    managedby='';
    startDate='';
    actorType='';
    actorIds='';
    tag='';
    modelName = sys.argv[1];

    if len(sys.argv) > 2:
        for arg in sys.argv[2:]:
            if arg.lower() == "analysisname":
                lastArg="analysisname"
            elif arg.lower() == "region":
                lastArg="region"
            elif arg.lower() == "businessunit":
                lastArg="businessunit"
            elif arg.lower() == "title":
                lastArg="title"
            elif arg.lower() == "category":
                lastArg="category"
            elif arg.lower() == "managedby":
                lastArg="managedby"
            elif arg.lower() == "startdate":
                lastArg="startdate"
            elif arg.lower() == "actortype":
                lastArg="actortype"
            elif arg.lower() == "tag":
                lastArg="tag"
            elif arg.lower() == "actors":
                lastArg="actors"
            elif arg.lower() == "signalprops":
                lastArg="signalprops"
            elif lastArg == "analysisname":
                analysisName=arg
                lastArg=''
            elif lastArg == "region":
                region=arg
                lastArg=''
            elif lastArg == "businessunit":
                businessunit=arg
                lastArg=''
            elif lastArg == "title":
                title=arg
                lastArg=''
            elif lastArg == "category":
                category=arg
                lastArg=''
            elif lastArg == "managedby":
                managedby=arg
                lastArg=''
            elif lastArg == "startdate":
                startDate=arg
                lastArg=''
            elif lastArg == "actortype":
                actorType=arg
                lastArg=''
            elif lastArg == "tag":
                tag=arg
                lastArg=''
            elif lastArg == "actors":
                actorIds=arg
                lastArg=''
            elif lastArg == "signalprops":
                signalProps=arg
                lastArg=''
            else:
                usage("Unrecognized argument: " + arg)

    # See SCM-2608
    if category.startswith('[object'):
        logging.info ("Stripping [object Object] from category!");
        category = '';

    argList.append("-m")
    argList.append(modelName)

    if len(analysisName) > 0:
        argList.append("-n")
        argList.append(analysisName)

    if len(region) > 0:
        argList.append("-r");
        argList.append(region);

    if len(businessunit) > 0:
        argList.append("-b");
        argList.append(businessunit);

    if len(title) > 0:
        argList.append("-t");
        argList.append(title);

    if len(category) > 0:
        argList.append("-c");
        argList.append(category);

    if len(managedby) > 0:
        argList.append("-M");
        argList.append(managedby);

    if len(startDate) > 0:
        argList.append("-d");
        argList.append(startDate);

    if len(actorType) > 0:
        argList.append("-T");
        argList.append(actorType);

    if len(tag) > 0:
        argList.append("-C");
        argList.append(tag);

    if len(actorIds) > 0:
        argList.append("-a");
        argList.append(actorIds);

    if len(signalProps) > 0:
        argList.append("-p");
        argList.append(signalProps);

    logging.info("xmRunDistributedPeerAnalysis processed args, modelName: [" + modelName + "]")

    try:
        logging.info("calling xmRunDistributedPeerAnalysis with args: [" + repr(argList) + "]")
        logging.info ("-------------------------------------------------------------------------------------")
        saUtils.runProcess(sys.argv[0], "xmRunDistributedPeerAnalysis", argList, False)

    except Exception as e:
        si.generateErrorResults(e)

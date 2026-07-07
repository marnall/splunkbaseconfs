# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import fnmatch
import os, platform, time
import re
import csv
import sys
import saUtils
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest
import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')

if __name__ == '__main__':
    name = ''
    app = ''
    status = ''
    model = ''
    description =''
    created_date =''
    last_updated = ''

    acquire = ''
    threshold = ''
    sequence = ''
    actor = ''
    actor_day_of_week = ''
    p2p = ''
    rule = ''
    relevancy = ''
    transaction = ''
    hazard = ''
    threat = ''

    rule_package = ''
    relevancy_graph = ''
    transaction_object = ''

    event_range = ''

    actor_actorid = ''
    actor_interval = ''
    actor_day = ''
    actor_hour = ''
    actor_day_of_month = ''

    actor_day_of_week_actorid = ''
    actor_day_of_week_interval = ''
    actor_day_of_week_day = ''
    actor_day_of_week_hour = ''
    actor_day_of_week_day_of_month = ''

    p2p_interval = ''
    p2p_day = ''
    p2p_hour = ''
    p2p_day_of_month = ''
    p2p_category = ''
    p2p_businessunit = ''
    p2p_managedby = ''
    p2p_title = ''
    p2p_tag = ''
    p2p_region = ''
    p2p_gender = ''
    p2p_actor_type = ''

    activate_date = ''
    activate_message = ''

    python3 = sys.version_info[0] >= 3
    rmode = "rb"
    wmode = "wb"
    if python3:
        rmode = "r"
        wmode = "w"

    try:

        if len(sys.argv) >21:
            for arg in sys.argv[1:]:
                if arg.lower().startswith('name='):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('app='):
                    eqsign = arg.find('=')
                    app = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('status='):
                    eqsign = arg.find('=')
                    status = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('model='):
                    eqsign = arg.find('=')
                    model = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('description='):
                    eqsign = arg.find('=')
                    description = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('created_date='):
                    eqsign = arg.find('=')
                    created_date = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('last_updated='):
                    eqsign = arg.find('=')
                    last_updated = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('acquire='):
                    eqsign = arg.find('=')
                    acquire = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('threshold='):
                    eqsign = arg.find('=')
                    threshold = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('sequence='):
                    eqsign = arg.find('=')
                    sequence = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor='):
                    eqsign = arg.find('=')
                    actor = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_week='):
                    eqsign = arg.find('=')
                    actor_day_of_week = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p='):
                    eqsign = arg.find('=')
                    p2p = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('rule='):
                    eqsign = arg.find('=')
                    rule = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('relevancy='):
                    eqsign = arg.find('=')
                    relevancy = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('transaction='):
                    eqsign = arg.find('=')
                    transaction = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('hazard='):
                    eqsign = arg.find('=')
                    hazard = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('threat='):
                    eqsign = arg.find('=')
                    threat = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('rule_package='):
                    eqsign = arg.find('=')
                    rule_package = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('relevancy_graph='):
                    eqsign = arg.find('=')
                    relevancy_graph = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('transaction_object='):
                    eqsign = arg.find('=')
                    transaction_object = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('event_range='):
                    eqsign = arg.find('=')
                    event_range = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('actor_actorid='):
                    eqsign = arg.find('=')
                    actor_actorid = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_interval='):
                    eqsign = arg.find('=')
                    actor_interval = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day='):
                    eqsign = arg.find('=')
                    actor_day = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_hour='):
                    eqsign = arg.find('=')
                    actor_hour = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_month='):
                    eqsign = arg.find('=')
                    actor_day_of_month = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('actor_day_of_week_actorid='):
                    eqsign = arg.find('=')
                    actor_day_of_week_actorid = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_week_interval='):
                    eqsign = arg.find('=')
                    actor_day_of_week_interval = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_week_day='):
                    eqsign = arg.find('=')
                    actor_day_of_week_day = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_week_hour='):
                    eqsign = arg.find('=')
                    actor_day_of_week_hour = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('actor_day_of_week_day_of_month='):
                    eqsign = arg.find('=')
                    actor_day_of_week_day_of_month = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('p2p_interval='):
                    eqsign = arg.find('=')
                    p2p_interval = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_day='):
                    eqsign = arg.find('=')
                    p2p_day = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_hour='):
                    eqsign = arg.find('=')
                    p2p_hour = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_day_of_month='):
                    eqsign = arg.find('=')
                    p2p_day_of_month = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_category='):
                    eqsign = arg.find('=')
                    p2p_category = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_businessunit='):
                    eqsign = arg.find('=')
                    p2p_businessunit = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_managedby='):
                    eqsign = arg.find('=')
                    p2p_managedby = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_title='):
                    eqsign = arg.find('=')
                    p2p_title = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_tag='):
                    eqsign = arg.find('=')
                    p2p_tag = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_region='):
                    eqsign = arg.find('=')
                    p2p_region = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_gender='):
                    eqsign = arg.find('=')
                    p2p_gender = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('p2p_actor_type='):
                    eqsign = arg.find('=')
                    p2p_actor_type = arg[eqsign+1:len(arg)]

                elif arg.lower().startswith('activate_date='):
                    eqsign = arg.find('=')
                    activate_date = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith('activate_message='):
                    eqsign = arg.find('=')
                    activate_message = arg[eqsign+1:len(arg)]
        else:
            raise Exception('xmSetAnalysisConfiguration-F-001: Usage: xmSetAnalysisConfiguration name=<string> app=<string> status=<string> model=<string> description=<string> created_date=<string> last_updated=<string> acquire=<string> threshold=<string> sequence=<string> actor=<string> actor_day_of_week=<string> p2p=<string> rule=<string> relevancy=<string> transaction=<string> hazard=<string> threat=<string> rule_package=<string> relevancy_graph=<string> transaction_object=<string> event_range=<string> actor_actorid=<string> actor_interval=<string> actor_day=<string> actor_hour=<string> actor_day_of_month=<string> actor_day_of_week_actorid=<string> actor_day_of_week_interval=<string> actor_day_of_week_day=<string> actor_day_of_week_hour=<string> actor_day_of_week_day_of_month=<string> p2p_interval=<string> p2p_day=<string> p2p_hour=<string> p2p_day_of_month=<string> p2p_category=<string> p2p_businessunit=<string> p2p_managedby=<string> p2p_title=<string> activate_date=<string> activate_message=<string>')

        if name == '':
            raise Exception("xmSetAnalysisConfiguration-F-002: parameter 'name' not found")
        elif model == '':
            raise Exception("xmSetAnalysisConfiguration-F-002: parameter 'model' not found")
        elif app == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'app' not found")
        elif created_date == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'created_date' not found")
        elif last_updated == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'last_updated' not found")
        elif acquire == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'acquire' not found")
        elif threshold == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'threshold' not found")
        elif sequence == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'sequence' not found")
        elif actor == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'actor' not found")
        elif actor_day_of_week == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'actor_day_of_week' not found")
        elif p2p == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'p2p' not found")
        elif rule == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'rule' not found")
        elif relevancy == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'relevancy' not found")
        elif transaction == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'transaction' not found")
        elif hazard == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'hazard' not found")
        elif threat == '':
            raise Exception("xmSetAnalysisConfiguration-F-003: parameter 'threat' not found")

        if description is None:
            description = ''

        if acquire is None:
            acquire = ''
        if threshold is None:
            threshold = ''
        if sequence is None:
            sequence = ''
        if actor is None:
            actor = ''
        if actor_day_of_week is None:
            actor_day_of_week = ''
        if p2p is None:
            p2p = ''
        if rule is None:
            rule = ''
        if relevancy is None:
            relevancy = ''
        if transaction is None:
            transaction = ''
        if hazard is None:
            hazard = ''
        if threat is None:
            threat = ''

        if rule_package is None:
            rule_package = ''
        if relevancy_graph is None:
            relevancy_graph = ''
        if transaction_object is None:
            transaction_object = ''

        if event_range is None:
            event_range = ''

        if actor_actorid is None:
            actor_actorid = ''
        if actor_interval is None:
            actor_interval = ''
        if actor_day is None:
            actor_day = ''
        if actor_hour is None:
            actor_hour = ''
        if actor_day_of_month is None:
            actor_day_of_month = ''

        if actor_day_of_week_actorid is None:
            actor_day_of_week_actorid = ''
        if actor_day_of_week_interval is None:
            actor_day_of_week_interval = ''
        if actor_day_of_week_day is None:
            actor_day_of_week_day = ''
        if actor_day_of_week_hour is None:
            actor_day_of_week_hour = ''
        if actor_day_of_week_day_of_month is None:
            actor_day_of_week_day_of_month = ''

        if p2p_interval is None:
            p2p_interval = ''
        if p2p_day is None:
            p2p_day = ''
        if p2p_hour is None:
            p2p_hour = ''
        if p2p_day_of_month is None:
            p2p_day_of_month = ''
        if p2p_category is None:
            p2p_category = ''
        if p2p_businessunit is None:
            p2p_businessunit = ''
        if p2p_managedby is None:
            p2p_managedby = ''
        if p2p_title is None:
            p2p_title = ''
        if p2p_tag is None:
            p2p_tag = ''
        if p2p_region is None:
            p2p_region = ''
        if p2p_gender is None:
            p2p_gender = ''
        if p2p_actor_type is None:
            p2p_actor_type = ''

        if activate_date is None:
            activate_date = ''
        if activate_message is None:
            activate_message = ''

        # Get property for model.directory
        modelDir = ''
        with open(saUtils.getScmPropertiesFileName()) as propertyFile:
            for line in propertyFile:
                propname, propval = line.partition("=")[::2]
                if propname.strip() == "model.directory":
                    modelDir = propval[:-1]

        splunkHome=os.environ.get('SPLUNK_HOME')
        modelDir = modelDir.replace("$(SPLUNK_HOME)",splunkHome)
        tmpName = name.replace(" ","_");
        theFile=modelDir + "/" + model + "/analysis_" + tmpName + "_configuration.csv"

        import csv
        with open(theFile, wmode) as fp:
            a = csv.writer(fp, delimiter=',')
            data = [[name,status,model,description,created_date,last_updated,acquire,threshold,sequence,actor,actor_day_of_week,p2p,rule,relevancy,transaction,hazard,threat,rule_package,relevancy_graph,transaction_object,event_range,actor_actorid,actor_interval,actor_day,actor_hour,actor_day_of_month,actor_day_of_week_actorid,actor_day_of_week_interval,actor_day_of_week_day,actor_day_of_week_hour,actor_day_of_week_day_of_month,p2p_interval,p2p_day,p2p_hour,p2p_day_of_month,p2p_category,p2p_businessunit,p2p_managedby,p2p_title,p2p_tag,p2p_region,p2p_gender,p2p_actor_type,activate_date,activate_message]]
            a.writerows(data)

        logger.info("xmSetAnalysisConfiguration - Saved Analysis Configuration: " + tmpName)
        print ("Response")
        print ("SUCCESS")

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)


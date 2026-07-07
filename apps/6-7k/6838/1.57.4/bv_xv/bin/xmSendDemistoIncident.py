# ==============================================================================
# Copyright 2023 BlueVoyant Inc. All Rights Reserved. Reproduction
# or unauthorized use is prohibited. Unauthorized use is illegal. Violators will
# be prosecuted. This software contains proprietary trade and business secrets.
# ==============================================================================
from __future__ import print_function
import os
import platform
import time
#import re
#import csv
#import sys
#import saUtils
import splunk.Intersplunk as si
#from xml.dom.minidom import parseString
#import splunk.rest

import logging as logger
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','scm-framework.log'),
     filemode='a')


import json
import argparse
import demisto

def options_handler():
    parser = argparse.ArgumentParser(description='Utility for batch action on incidents')
    parser.add_argument('-u', '--user', help='The username for the login', required=True)
    parser.add_argument('-p', '--password', help='The password for the login', required=True)
    parser.add_argument('-s', '--server', help='The server URL to connect to', required=True)
    parser.add_argument('-n', '--name', help='Incident name', required=True)
    parser.add_argument('-t', '--type', help='Incident Type')
    parser.add_argument('-sev', '--severity', help='Incident Severity', default='Unknown', choices=['Critical', 'High', 'Medium', 'Low', 'Informational','Unknown'])
    parser.add_argument('-o', '--owner', help='Incident Owner')
    parser.add_argument('-d', '--details', help='Incident Details')
    parser.add_argument('-l', '--labels', help='Incident Labels, in the format [{"type":"t","value":"v"},{"type":"t2","value":"v2"}]')
    parser.add_argument('-c','--custom_fields', help='The json that includes the values for the custom fields, in the format {\'alertsource\': \'vc\',\'datetimecreated\': \'Wed, 15 Feb 2017 13:05:13 GMT\'}')
    options = parser.parse_args()

    return options


def severity_to_number(severity_str):
    return {
        'Critical': 4,
        'High': 3,
        'Medium': 2,
        'Low': 1,
        'Informational': 0.5,
        'Unknown': 0
    }[severity_str]

def main():
    try:
        print ("Response")
        options = options_handler()
        c = demisto.DemistoClient(options.user, options.password, options.server)
        c.Login()

        labels = None
        if (options.labels is not None) and len(options.labels) > 0 :
            labels = json.loads(options.labels)
        fields = None
        if (options.custom_fields is not None) and len(options.custom_fields) > 0 :
            fields = json.loads(options.custom_fields)
        r = c.CreateIncident(options.name, options.type, severity_to_number(options.severity), options.owner, labels, options.details, fields)
        print(r)

        print ("SUCCESS")
        logger.info("xmSendIncident - : " + title);

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

    except Exception as e:
        si.generateErrorResults(e)

if __name__ == '__main__':
    main()




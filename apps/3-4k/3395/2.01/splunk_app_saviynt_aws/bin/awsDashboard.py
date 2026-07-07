import httplib
from urlparse import urlparse
import logging
import sys,os,splunk.Intersplunk
import csv
import time
import json
import requests
import base64
from oAuthToken import validateOrGetOAuthToken
from validateConnection import getMessage

logger = logging.getLogger('splunk.saviynt')
logger.info("Popluating AWS Dashboard CSVs")

'''
    Get the data for AWS Dashboard (pie chart) and store in lookups.
'''
def createAwsDashboard(gatewayurl,OAUTH_TOKEN,pemType):
    csv_data = None
    try:
        
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        LOOKUP_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/lookups/"
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        STATIC_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/static/"
        logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
        logger.info("LOOKUP_HOME is:"+LOOKUP_HOME)
        logger.info("CONF_HOME is:"+CONF_HOME)
        logger.info("STATIC_HOME is:"+STATIC_HOME)

        #Reading the external config file
        logger.info("Reading the external config file")
        awstriggerdataimport = ''
        connectiontype = ''
        systemname = ''
        gatewayserver = ''
        gatewayusername = ''
        gatewaysavpdenc = ''
        gatewaysavpd = ''
        Savusername = ''
        Savsavpd = ''
        conf_read_file_path = CONF_HOME + "externalconfig.txt"
        logger.info("Config file is:"+conf_read_file_path)
        conf_read = open(conf_read_file_path, 'r')
        for line in conf_read:
            conf,value = line.split(":=:")
            if (conf.strip().lower() == 'savname'):
                Savusername = value.strip()
            if (conf.strip().lower() == 'savmessage'):
                savsavpdenc = value.strip()
                Savsavpd = getMessage(savsavpdenc)
        conf_read.close()

        WEBSERVICE_URl = gatewayurl + "/restful/queryResults"
        logger.info("Webservice url:"+WEBSERVICE_URl)
        pemPath = CONF_HOME + "pemfile.pem"
        
    #Reading the qyery file
        csv_read = open("create_aws_dashboard_list.txt", 'r')
        logger.info("Opened create_aws_dashboard_list file")
        for line in csv_read:
            lookupname,query = line.split("::::")
            csv_write = LOOKUP_HOME + lookupname

            logger.info("Writing into: "+csv_write)
            results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

            OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
            authorization = "Bearer "+ OAUTH_TOKEN
            json_out = requests.post(WEBSERVICE_URl, data = {'query':query},headers={'Authorization':authorization},verify=pemPath)
            json_data = json.loads(json_out.text)
            
            # open a file for writing
            csv_data = open(csv_write, 'wb')
            csv_data.truncate(0)
         
            # create the csv writer object
            csvwriter = csv.writer(csv_data,quoting=csv.QUOTE_NONNUMERIC)
            logger.info("CSV Writer created")
            count = 0

            for var in json_data:
                if count == 0:
                    header = var.keys()
                    csvwriter.writerow(header)
                    count += 1
                csvwriter.writerow(var.values())
            csv_data.close()
            logger.info("Inserted the data in csv")
            
        csv_read.close()
        logger.info("Completed populating AWS Dashboard CSVs.") 

    except Exception, ex:
        logger.exception(ex)
        raise
    finally:
        if csv_data is not None:
            csv_data.close()

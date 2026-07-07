import sys,os,splunk.Intersplunk
import csv
import time
import json
import requests
import logging
import base64
from oAuthToken import validateOrGetOAuthToken
from validateConnection import getMessage

logger = logging.getLogger('splunk.saviynt')
'''
    Get the user and account details and store in lookups.
'''
def createSecurityLookup(gatewayurl,OAUTH_TOKEN,pemType):
    csv_data = None
    csv_read = None

    try:
        logger.info("Populating Security Lookup CSVs")
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        LOOKUP_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/lookups/"
        logger.info("CONF_HOME is:"+CONF_HOME)
        logger.info("LOOKUP_HOME is:"+LOOKUP_HOME)
        
        #Reading the config file
        logger.info("Reading the config file")
        awstriggerdataimport = ''
        Savusername = ''
        Savsavpd = ''
        connectiontype = ''
        systemname = ''
        conf_read_file_path = CONF_HOME + "externalconfig.txt"
        logger.info("Config file is:"+conf_read_file_path)
        conf_read = open(conf_read_file_path, 'r')
        for line in conf_read:
            conf,value = line.split(":=:")
            if (conf.strip().lower() == 'savname'):
                Savusername = value.strip()
            if (conf.strip().lower() == 'savmessage'):
                Savsavpdenc = value.strip()
                Savsavpd = getMessage(Savsavpdenc)
        conf_read.close()

        WEBSERVICE_URl = gatewayurl + "/restful/queryResults"
        pemPath = CONF_HOME + "pemfile.pem"
        
        csv_read = open("create_security_lookup_list.txt", 'r')
        
        for line in csv_read:
            lookupname,query = line.split("::::")
            csv_write = LOOKUP_HOME + lookupname
            
            logger.info("Writing into :"+ lookupname)
            
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
            

    except Exception, ex:
        logger.exception(ex)
        raise
    finally:
        if csv_read is not None:
            csv_read.close()
        if csv_data is not None:
            csv_data.close()

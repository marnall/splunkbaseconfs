import sys,splunk.Intersplunk,os
import csv
import time
import json
import requests
import logging
import splunk
import base64

from oAuthToken import validateOrGetOAuthToken
from create_security_lookup import createSecurityLookup
from awsDashboard import createAwsDashboard
from validateConnection import getMessage
from awsDashboardTable import createAwsDashboardTable           

results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
logger = logging.getLogger('splunk.saviynt')

'''
    Pull the data and store in lookups
'''

def pullData(sysName,URL,OAUTH_TOKEN,pemType):
    csv_data = None
    try:
        #Paths
        logger.info("Pulling data to Splunk")
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        LOOKUP_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/lookups/"
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
        logger.info("LOOKUP_HOME is:"+LOOKUP_HOME)
        logger.info("CONF_HOME is:"+CONF_HOME)

        #Reading the config file and get the connection paramters
        logger.info("Reading the config file")
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
                Savsavpdenc = value.strip()
                Savsavpd = getMessage(Savsavpdenc)
        conf_read.close()
        logger.info("URL is: "+URL)

        #List of URL
        runAllControlsURL = URL+'/restful/runAnalyticsControls'
        checkJobStatusURL = URL+'/restful/checkJobStatus'
        fetchControlListURL = URL+'/restful/fetchControlList'
        fetchControlDetailsURL = URL+'/restful/fetchControlDetails'
        
        logger.info("runAllControlsURL is:"+runAllControlsURL)
        logger.info("checkJobStatusURL is:"+checkJobStatusURL)
        logger.info("fetchControlListURL is:"+fetchControlListURL)
        logger.info("fetchControlDetailsURL is:"+fetchControlDetailsURL)

        pemPath = CONF_HOME + "pemfile.pem"

        #Run all controls parameters
        jobgroup = 'Analytics'
        jobname = 'AnalyticsJob'
        analyticsCategories = '###EC2###IAM###Redshift###S3###VPC###ELB###CloudFormation###RDS###CloudTrail###EBS###'
        analyticsApplication = '###'+sysName+'###'
        
        #Check Job Status parameters
        jobgroup1 = 'Analytics'
        jobname1 = 'AnalyticsJob'
            
        #Run all Controls
        OAUTH_TOKEN = validateOrGetOAuthToken(URL,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
        logger.info("OAUTH_TOKEN=%s" % OAUTH_TOKEN)
        authorization = "Bearer "+ OAUTH_TOKEN
        json_controls = requests.post(runAllControlsURL,data = {'jobgroup':jobgroup,'jobname':jobname,'analyticsCategories':analyticsCategories,'analyticsApplications':analyticsApplication},headers={'Authorization':authorization},verify=pemPath)
        json_controls_data = json.loads(json_controls.text)
        logger.info(json_controls_data['msg'])

        status = 'NOT STARTED'
        count = 0
        while (status.lower()=='not started' or status.lower()=='in-progress'):
            if count==0:
                time.sleep(60)
                count += 1
            OAUTH_TOKEN = validateOrGetOAuthToken(URL,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
            logger.info("OAUTH_TOKEN=%s" % OAUTH_TOKEN)
            authorization = "Bearer "+ OAUTH_TOKEN
            json_status = requests.post(checkJobStatusURL,data = {'jobgroup':jobgroup1,'jobname':jobname1},headers={'Authorization':authorization},verify=pemPath)
            json_status_data = json.loads(json_status.text)
            status = json_status_data['msg']
            time.sleep(60)
            logger.info(status)

        #Fetch Controls list
        logger.info(status)
        if(status.lower()=='completed'):
            logger.info("Status is completed. Fetching list of controls")
            OAUTH_TOKEN = validateOrGetOAuthToken(URL,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
            authorization = "Bearer "+ OAUTH_TOKEN
            json_list = requests.post(fetchControlListURL,data={'category':analyticsCategories,'application':analyticsApplication},headers={'Authorization':authorization},verify=pemPath)
            json_list_data = json.loads(json_list.text)
            logger.info(json_list_data['msg'])

    #Writing control list into a lookup
            
            #open a file for writing
            csv_file = LOOKUP_HOME + "controllist.csv"
            csv_data = open(csv_file, 'wb')
            csv_data.truncate(0)

            #create the csv writer object
            csvwriter = csv.writer(csv_data,quoting=csv.QUOTE_NONNUMERIC)
            logger.info("CSV Writer created")
            count = 0
            
            csvwriter.writerow(["analyticsId","application","analyticsName","category","description","lastRun","risk","recommendations","conflictCount"])
                  
            logger.info("Writing control list into controllist.csv")
            for var in json_list_data['controls']:   
                analyticsId = var['analyticsId']
                application = var['application']
                analyticsName = var['analyticsName']
                controlName,systemName = analyticsName.rsplit("_",1)
                category = var['category']
                description = var['description']
                lastRun = var['lastRun']
                risk = var['risk']
                recommendations = var['recommendations']
                conflictCount = var['conflictCount']
                csvwriter.writerow([analyticsId,application,controlName,category,description,lastRun,risk,recommendations,conflictCount])

            csv_data.close()
            logger.info("Inserted the data into controllist.csv")

    #Read control list and create individual lookups

            #open a file for reading
            logger.info("Reading controllist")
            csv_read = open(csv_file, 'r')
            csvreader = csv.DictReader(csv_read)
            headers = csvreader.fieldnames
            logger.info(headers)

            for line in csvreader:
                controlId = line['analyticsId']
                controlName = line['analyticsName']
                logger.info("Analytics Id is:"+controlId)
                csv_write = LOOKUP_HOME + controlId + ".csv"
                logger.info("Control details lookup name is:"+csv_write)
                logger.info("Fetching control details for analyticsId: "+controlId)
                OAUTH_TOKEN = validateOrGetOAuthToken(URL,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
                authorization = "Bearer "+ OAUTH_TOKEN
                json_out = requests.post(fetchControlDetailsURL, data = {'controlId':controlId},headers={'Authorization':authorization},verify=pemPath)
                json_data = json.loads(json_out.text)
                logger.info(json_data['msg'])

                # open a file for writing
                csv_data = open(csv_write, 'wb')
                csv_data.truncate(0)

                # create the csv writer object
                csvwriter = csv.writer(csv_data,quoting=csv.QUOTE_NONNUMERIC)
                logger.info("CSV Writer created")
                count = 0

                logger.info("Writing into control details lookup")
                for var in json_data['controlDetails']:
                    if count == 0:
                        header = var.keys()
                        csvwriter.writerow(header)
                        count += 1
                    csvwriter.writerow(var.values())
                csv_data.close()
                logger.info("Inserted the data into "+csv_write)
                
            csv_read.close()
            logger.info("Done iterating the control list")
            logger.info("Done creating all the control detail lookups")

            createAwsDashboard(URL,OAUTH_TOKEN,pemType)
            createAwsDashboardTable(URL,OAUTH_TOKEN,pemType)
            createSecurityLookup(URL,OAUTH_TOKEN,pemType)

    except Exception, ex:
        logger.exception(ex)
        raise
        
    finally:
        if csv_data is not None:
            csv_data.close()

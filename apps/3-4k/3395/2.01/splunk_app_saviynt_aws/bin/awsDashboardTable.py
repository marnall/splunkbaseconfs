import sys,splunk.Intersplunk,os
import csv
import time
import json
import requests
import logging
import splunk
import base64
import logging
from oAuthToken import validateOrGetOAuthToken
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
from validateConnection import getMessage
logger = logging.getLogger('splunk.saviynt')

'''
    Get the data for AWS Dashboard (bubble chart and tiles) and store in lookups.
'''
def createAwsDashboardTable(gatewayurl,OAUTH_TOKEN,pemType):
    csv_data = None
    csv_data2 = None
    try:
        
        logger.info("Populating AWS Dashboard Table")
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        LOOKUP_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/lookups/"
        logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
        logger.info("CONF_HOME is:"+CONF_HOME)
        logger.info("LOOKUP_HOME is:"+LOOKUP_HOME)
        
        controlList = LOOKUP_HOME+'controllist.csv'
        violationsCount = {'EC2':0,'IAM':0,'RDS':0,'ELB':0,'S3':0,'CLOUDTRAIL':0,'EBS':0,'VPC':0,'REDSHIFT':0,'CLOUDFORMATION':0}
        logger.info("Opening the file :" + controlList)
        try:
            with open(controlList, 'rb') as csvfile:
                logger.info("Controllist csv file opened")
                reader = csv.reader(csvfile, delimiter=',')                                                                                                                                 
                header = reader.next()  
                categoryIndex = header.index("category")
                voilationsIndex = header.index("conflictCount")
               
                for row in reader:  
                    categoryName = row[categoryIndex].upper()
                    if categoryName in violationsCount:
                        violationsCount[categoryName]=violationsCount[categoryName]+int(row[voilationsIndex])
        except Exception,ex:
            logger.info(ex)
                
        logger.info(violationsCount)
                
        #Reading the config file
        logger.info("Reading the config file")
        awstriggerdataimport = 'true'
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
        
        dashboardname = "###All Active###"
        
        #List of URL
        connURL = gatewayurl+'/restful/retrieveDashboardData'
        
        logger.info("DashboardTable URL is:"+connURL)
            
        #Pull Data
        pemPath = CONF_HOME + "pemfile.pem"
        
        logger.info("Pull dashboard data")
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,pemType)
        authorization = "Bearer " + OAUTH_TOKEN
        json_out = requests.post(connURL,data={'dashboardname':dashboardname},headers={'Authorization':authorization},verify=pemPath)
        json_out_data = json.loads(json_out.text)
        logger.info(json_out_data)
        logger.info(json_out_data['dashboardData'])
            
        # open a file for writing
        logger.info("Writing into dashboardTable csv file")
        conf_write_file_path = LOOKUP_HOME + "dashboardtable.csv"
        logger.info("Writable file is:"+conf_write_file_path)
        csv_data = open(conf_write_file_path, "wb")
        csv_data.truncate(0)
        
        # create the csv writer object
        csvwriter = csv.writer(csv_data,quoting=csv.QUOTE_NONNUMERIC)
        logger.info("CSV Writer created")
        
        #dashboardTable csv
        count = 0
        for var in json_out_data['dashboardData']:
            if count == 0:
                header = var.keys()
                csvwriter.writerow(header)
                count += 1
            csvwriter.writerow(var.values())
        csv_data.close()
        
        #bubble chart data
        logger.info("Writing into instanceViolations csv file")
        conf_write_file_path2 = LOOKUP_HOME + "instanceViolations.csv"
        logger.info("Writable file is:"+conf_write_file_path2)
        csv_data2 = open(conf_write_file_path2, "wb")
     
        category = {'EC2':{},'IAM':{},'RDS':{},'ELB':{},'S3':{},'CLOUDTRAIL':{},'EBS':{},'VPC':{},'REDSHIFT':{},'CLOUDFORMATION':{}}
        
        if (json_out_data['msg'] == 'SUCCESS'):
            i=0
            logger.info("Parsing data for bubble chart")
            csv_data2.truncate(0)
            logger.info("CSV Writer created")
            csvwriter2 = csv.writer(csv_data2,quoting=csv.QUOTE_NONNUMERIC)
            for var in json_out_data['dashboardData']:
                type = json_out_data['dashboardData'][i]['category']
                categoryData = {}
                if (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active EC2 Instances"):
                    categoryData = category['EC2']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['EC2'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active IAM Objects"):
                    categoryData = category['IAM']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['IAM'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active RDS Instances"):
                    categoryData = category['RDS']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['RDS'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active S3 Buckets"):
                    categoryData = category['S3']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['S3'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active ELB Instances"):
                    categoryData = category['ELB']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['ELB'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active CloudTrail Instances"):
                    categoryData = category['CLOUDTRAIL']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['CLOUDTRAIL'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active EBS Instances"):
                    categoryData = category['EBS']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['EBS'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active VPC Instances"):
                    categoryData = category['VPC']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['VPC'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active RedShift Instances"):
                    categoryData = category['REDSHIFT']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['REDSHIFT'] = categoryData
                elif (json_out_data['dashboardData'][i]['dashboard_name'] == "All Active CloudFormation Instances"):
                    categoryData = category['CLOUDFORMATION']
                    categoryData['tile_count'] = json_out_data['dashboardData'][i]['tile_count']
                    category['CLOUDFORMATION'] = categoryData
                i = i+1
            
            logger.info("Writing into bubble csv")
            csvwriter2.writerow(["Category", "Instances", "Violations", "Size"])
            for key in category:
                tile_count = "0"
                violations = "0"
                violations = violationsCount[key]
                if('tile_count' in category[key]):
                    tile_count = category[key]['tile_count']
                csvwriter2.writerow([key,tile_count,violations,violations])
        
        csv_data2.close()
        
        logger.info("Inserted the data in bubbleCsv successfully")
        
    except Exception, ex:
        logger.exception(ex)
        raise
    finally:
        if csv_data is not None:
            csv_data.close()
        if csv_data2 is not None:
            csv_data2.close()

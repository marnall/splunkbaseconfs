import sys,splunk.Intersplunk,os
import csv
import time
import json
import requests
import logging, logging.handlers
import splunk
import copy
from awsInstanceConnection import startInstance
from awsInstanceConnection import stopInstance
from time import sleep
from createLogs import setup_logging
import httplib
from urlparse import urlparse
from requests.exceptions import ConnectionError
from recreateInstanceEmail import sendRecreateInstanceEmail
from oAuthToken import validateOrGetOAuthToken
from pulldata import pullData
from validateConnection import setMessage
from validateConnection import getMessage

logger = setup_logging()
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
'''
    Write to the External Config text file
'''
def writeToExternalConfig():
    conf_write_ext = None
    try:
        if(externalConfigRead):
            logger.info("Writing into externalconfig.txt file")
            conf_write_file_path_ext = CONF_HOME + "externalconfig.txt"
            logger.info("Config file is:"+conf_write_file_path_ext)
            conf_write_ext = open(conf_write_file_path_ext, "w")
            conf_write_ext.write("awstriggerdataimport:=:%s\n" % awstriggerdataimport)
            conf_write_ext.write("connectiontype:=:%s\n" % connectiontype)
            conf_write_ext.write("systemname:=:%s\n" % systemname)
            conf_write_ext.write("server_access_key_id:=:%s\n" % gateway_access_key_id)
            conf_write_ext.write("server_secret_access_key:=:%s\n" % gateway_secret_access_key)
            conf_write_ext.write("server_role_arn:=:%s\n" % gateway_role_arn)
            conf_write_ext.write("server_role_session_name:=:%s\n" % gateway_role_session_name)
            conf_write_ext.write("serverurl:=:%s\n" % gatewayserver)
            conf_write_ext.write("servername:=:%s\n" % gatewayusername)
            conf_write_ext.write("servermessage:=:%s\n" % gatewaysavpdenc)
            conf_write_ext.write("instance:=:%s\n" % instance)
            conf_write_ext.write("aws_stack_role_name:=:%s\n" % aws_stack_role_name)
            conf_write_ext.write("savname:=:%s\n" % Savusername)
            savsavpdenc = setMessage(Savsavpd)
            conf_write_ext.write("savmessage:=:%s\n" % savsavpdenc)
            logger.info("Written into externalconfig.txt file.")
    except Exception, ex:
        logger.info(ex)
        raise
    finally:
        if conf_write_ext is not None:
            conf_write_ext.close()

'''
    Store user's connection data into testconn file
'''            
def writeToTestConn():
    conf_write = None
    try:
        if(testConnRead):
            logger.info("Writing into textconn.txt file")
            conf_write_file_path = STATIC_HOME + "testconn.txt"
            logger.info("Config file is:"+conf_write_file_path)
            conf_write = open(conf_write_file_path, "w")
            conf_write.truncate()
            conf_write.write("cloudenabled:=:%s\n" % cloudenabled)
            conf_write.write("connection:=:%s\n" % connection1)
            if(cloudenabled=="false"):
                conf_write.write("AWS_ACCESS_KEY:=:%s\n" % AWS_ACCESS_KEY)
                conf_write.write("AWS_ACCESS_SECRET_savpd:=:%s\n" % AWS_ACCESS_SECRET_savpd)
            conf_write.write("AWS_ACCOUNT_ID:=:%s\n" % AWS_ACCOUNT_ID)
            conf_write.write("CROSS_ACCOUNT_ROLE_ARN:=:%s\n" % CROSS_ACCOUNT_ROLE_ARN)
            conf_write.write("CONNSTATUS:=:%s\n" % CONNSTATUS)
            conf_write.write("INSTANCESTATUS:=:%s\n" % INSTANCESTATUS)
            conf_write.write("IMPORTSTATUS:=:%s\n" % IMPORTSTATUS)
            conf_write.write("ISACTIVE:=:%s\n" % ISACTIVE)
            conf_write.write("IS_ACCOUNT_ACTIVATED:=:%s\n" % IS_ACCOUNT_ACTIVATED)
            conf_write.write("SPLUNK_ID:=:%s\n" % splunkid)
            conf_write.write("FIRST_NAME:=:%s\n" % firstname)
            conf_write.write("LAST_NAME:=:%s\n" % lastname)
            conf_write.write("EMAIL:=:%s\n" % email)
            conf_write.write("PHONE:=:%s\n" % phone)
            conf_write.write("timestamp:=:%s\n" % timestamp)
            conf_write.write("OAUTH_TOKEN:=:%s\n" % OAUTH_TOKEN)
            logger.info("Written into testconn text file.") 
    except Exception, ex:
        logger.info(ex)
        raise
    finally:
        if conf_write is not None:
            conf_write.close()

'''
    Create connetion with Saviynt
'''
def gateway():
    reCreateInstanceReason = ""
    oldInstance = ""
    global OAUTH_TOKEN
    global instanceStarted
    try:
        logger.info("Got the customer name " + connection)
        logger.info("Trying to create")
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,gatewayusername,gatewaysavpd,oAuthPemServer)
        logger.info("OAUTH_TOKEN=%s" % OAUTH_TOKEN)
        authorization = "Bearer "+ OAUTH_TOKEN
        json_status = requests.post(WEBSERVICE_URL, data = {'customerName':connection},headers={'Authorization':authorization},verify=pemPathServer,timeout=2000)
        
        json_status_data = json.loads(json_status.text)
        logger.info("Got json data")
        
        global CONNSTATUS
        global Savusername
        global Savsavpd
        global instance
        global return_message
        global aws_stack_role_name
        Savusername = ""
        Savsavpd = ""
        instance = ""
        aws_stack_role_name = ""
        global INSTANCESTATUS
        if(json_status_data['msg'].lower() == "failed"):
            logger.info("Failed to create.")
            return_message = "Failed to create connection."
        else:
            details = json_status_data['stackDetails']
            if('stackReason' in details and details['stackReason'] is not None):
                logger.info("CONNREASON = " +details['stackReason'])
                reCreateInstanceReason = "Reason: "+details['stackReason']+", stackStatus: "+details['stackStatus']
            
            CONNSTATUS = details['stackStatus']
            logger.info(details['stackStatus'])
            if(details['stackStatus'] == 'CREATE_COMPLETE'):
                Savusername = details['username']
                Savsavpd = details['password']
                
                SaviyntUrl = details['stackURL']
                instance,aws_stack_role_name = SaviyntUrl.split("##")

                writeToExternalConfig()
                minutes = 0
                limitMinutes = 20
                if (instance is not None and instance != ""):
                    INSTANCESTATUS = "TRUE"
                    instanceStarted = "true"
                else:
                    instanceStarted = "false"
        logger.info("end of create")
    except Exception, ex:
        logger.exception(ex)
        try:
            global CONNSTATUS
            CONNSTATUS = "Import Failed"
            instanceStarted = "false"
            reCreateInstanceReason = "Gateway did not create instance." + reCreateInstanceReason +". "+str(ex)
            sendRecreateInstanceEmail(reCreateInstanceReason,oldInstance,splunkid,firstname,lastname,email,phone,connection)
        except Exception, ex:
            logger.info("Server Failed to start import process and could not inform Saviynt")
        raise

#Variables declared
return_message = "Import Failed"
importSuccessFlag = False
isOtherProcessRunning = True
saveconnection = 'Y'
appType = "FREE"
gatewayurl = ''
oAuthPemServer = "server"
oAuthPemInstance = "instance"

externalConfigRead = False
logger.info("Reading the external config file")
awstriggerdataimport = ''
connectiontype = ''
systemname = ''
gateway_access_key_id = ""
gateway_secret_access_key = ""
gateway_role_arn = ""
gateway_role_session_name= ""
gatewayserver = ''
gatewayusername = ''
gatewaysavpdenc = ''
gatewaysavpd = ''
Savusername = ''
Savsavpd = ''
instance = None
aws_stack_role_name = ''
 
testConnRead = False
cloudenabled = ''
connection = ''
connection1 = ''
AWS_ACCESS_KEY = ''
AWS_ACCESS_SECRET_savpd = ''
AWS_ACCOUNT_ID = ''
CROSS_ACCOUNT_ROLE_ARN = ''
CONNSTATUS = "Connection Failed"
INSTANCESTATUS = ''
IMPORTSTATUS = "false"
instanceStarted = "true"
ISACTIVE = "false"
IS_ACCOUNT_ACTIVATED = ''
splunkid = ''
firstname = ''
lastname = ''
email = ''
phone = ''
timestamp = '' 
OAUTH_TOKEN = None 
testConnBackupData = {}
   
#paths
SPLUNK_HOME = ""
LOOKUP_HOME = ""
CONF_HOME = ""
STATIC_HOME = ""
WEBSERVICE_URL = ""
pemPath = ""
pemPathServer = ""

try:
    #Paths
    SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    LOOKUP_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/lookups/"
    CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
    STATIC_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/static/"
    logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
    logger.info("LOOKUP_HOME is:"+LOOKUP_HOME)
    logger.info("CONF_HOME is:"+CONF_HOME)
    logger.info("STATIC_HOME is:"+STATIC_HOME)
    
    #Create the lookup directory if missing
    try:
        if os.path.exists(LOOKUP_HOME) == False:
           logger.info("LOOKUP_HOME doesn't exist..Creating one")
           os.mkdir(LOOKUP_HOME,0777)
           logger.info("LOOKUP_HOME Created")
    except Exception, ex:
        logger.info(ex)
        
    #Reading the testconn file to get user's connection details
    logger.info("Reading the testconn file")
    conn_read_file_path = STATIC_HOME + "testconn.txt"
    logger.info("Connection file is:"+conn_read_file_path)
    conn_read = open(conn_read_file_path, 'r')
    value = ''
    for line in conn_read:
        conn,value = line.split(":=:")
        if (conn.strip().lower() == 'cloudenabled'):
            cloudenabled = value.strip()
            testConnBackupData['cloudenabled']=cloudenabled
            logger.info("cloudenabled value is: "+cloudenabled)
        if (conn.strip().lower() == 'connection'):
            connection1 = value.strip()
            testConnBackupData['connection']=connection1
            connection = connection1.replace(" ","")
            logger.info("connection value is: "+connection)
        if (conn.strip() == 'AWS_ACCESS_KEY'):
            AWS_ACCESS_KEY = value.strip()
            testConnBackupData['AWS_ACCESS_KEY']=AWS_ACCESS_KEY
        if (conn.strip() == 'AWS_ACCESS_SECRET_savpd'):
            AWS_ACCESS_SECRET_savpd = value.strip()
            testConnBackupData['AWS_ACCESS_SECRET_savpd']=AWS_ACCESS_SECRET_savpd
        if (conn.strip() == 'AWS_ACCOUNT_ID'):
            AWS_ACCOUNT_ID = value.strip()
            testConnBackupData['AWS_ACCOUNT_ID']=AWS_ACCOUNT_ID
        if (conn.strip() == 'CROSS_ACCOUNT_ROLE_ARN'):
            CROSS_ACCOUNT_ROLE_ARN = value.strip()
            testConnBackupData['CROSS_ACCOUNT_ROLE_ARN']=CROSS_ACCOUNT_ROLE_ARN
        if (conn.strip() == 'CONNSTATUS'):
            CONNSTATUS = value.strip()
            testConnBackupData['CONNSTATUS']=CONNSTATUS
            logger.info("CONNSTATUS value is: "+CONNSTATUS)
        if (conn.strip() == 'INSTANCESTATUS'):
            INSTANCESTATUS = value.strip()
            testConnBackupData['INSTANCESTATUS']=INSTANCESTATUS
        if (conn.strip() == 'IMPORTSTATUS'):
            IMPORTSTATUS = value.strip()
            testConnBackupData['IMPORTSTATUS']=IMPORTSTATUS
            logger.info("IMPORTSTATUS value is: "+IMPORTSTATUS)
        if (conn.strip() == 'ISACTIVE'):
            ISACTIVE = value.strip()
            testConnBackupData['ISACTIVE']=ISACTIVE
            logger.info("ISACTIVE value is: "+ISACTIVE)
        if (conn.strip() == 'IS_ACCOUNT_ACTIVATED'):
            IS_ACCOUNT_ACTIVATED = value.strip()
            testConnBackupData['IS_ACCOUNT_ACTIVATED']=IS_ACCOUNT_ACTIVATED
            logger.info("IS_ACCOUNT_ACTIVATED value is: "+IS_ACCOUNT_ACTIVATED)
        if (conn.strip() == 'SPLUNK_ID'):
            splunkid = value.strip()
            testConnBackupData['SPLUNK_ID']=splunkid
            logger.info("SPLUNK ID value is: "+splunkid)
        if (conn.strip() == 'FIRST_NAME'):
            firstname = value.strip()
            testConnBackupData['FIRST_NAME']=firstname
            logger.info("Firstname value is: "+firstname)
        if (conn.strip() == 'LAST_NAME'):
            lastname = value.strip()
            testConnBackupData['LAST_NAME']=lastname
            logger.info("Lastname value is: "+lastname)
        if (conn.strip() == 'EMAIL'):
            email = value.strip()
            testConnBackupData['EMAIL']=email
            logger.info("Email value is: "+email)
        if (conn.strip() == 'PHONE'):
            phone = value.strip()
            testConnBackupData['PHONE']=phone
            logger.info("Phone value is: "+phone)
        if (conn.strip() == 'timestamp'):
            timestamp = value.strip()
            testConnBackupData['timestamp']=timestamp
            logger.info("Timestamp value is: "+timestamp)
        if (conn.strip() == 'OAUTH_TOKEN'):
            OAUTH_TOKEN = value.strip()
            testConnBackupData['OAUTH_TOKEN']=OAUTH_TOKEN
            logger.info("OAUTH_TOKEN value is: "+OAUTH_TOKEN)
    testConnRead = True
    conn_read.close()

    #Ensure that no other job is running
    if (IMPORTSTATUS.lower() == "false"):
        isOtherProcessRunning = False
        IMPORTSTATUS = "true"
        writeToTestConn()

    #Reading the external config file
        logger.info("Reading the external config file")
        conf_read_file_path = CONF_HOME + "externalconfig.txt"
        logger.info("Config file is:"+conf_read_file_path)
        conf_read = open(conf_read_file_path, 'r')
        for line in conf_read:
            conf,value = line.split(":=:")
            if (conf.strip().lower() == 'awstriggerdataimport'):
                awstriggerdataimport = value.strip()
                logger.info("awstriggerdataimport value is: "+awstriggerdataimport)
            if (conf.strip().lower() == 'connectiontype'):
                connectiontype = value.strip()
                logger.info("connectiontype value is: "+connectiontype)
            if (conf.strip().lower() == 'systemname'):
                systemname = value.strip()
                logger.info("systemname value is: "+systemname) 
            if (conf.strip().lower() == 'server_access_key_id'):
                gateway_access_key_id = value.strip()
            if (conf.strip().lower() == 'server_secret_access_key'):
                gateway_secret_access_key = value.strip()
            if (conf.strip().lower() == 'server_role_arn'):
                gateway_role_arn = value.strip()
            if (conf.strip().lower() == 'server_role_session_name'):
                gateway_role_session_name = value.strip()
            if (conf.strip().lower() == 'serverurl'):
                gatewayserver = value.strip()
                logger.info("AWS server value is: "+gatewayserver)
            if (conf.strip().lower() == 'servername'):
                gatewayusername = value.strip()
            if (conf.strip().lower() == 'servermessage'):
                gatewaysavpdenc = value.strip()
                gatewaysavpd = getMessage(gatewaysavpdenc)
            if (conf.strip().lower() == 'instance'):
                instance = value.strip()
            if (conf.strip().lower() == 'aws_stack_role_name'):
                aws_stack_role_name = value.strip()
            if (conf.strip().lower() == 'savname'):
                Savusername = value.strip()
            if (conf.strip().lower() == 'savmessage'):
                savsavpdenc = value.strip()
                Savsavpd = getMessage(savsavpdenc)
        externalConfigRead = True
        conf_read.close()

        systemname = connection

    #List of URL
        WEBSERVICE_URL = gatewayserver+'/ws/rest/provisionAWSInstance'
        logger.info("WEBSERVICE URL is:"+WEBSERVICE_URL)  

        pemPath = CONF_HOME + "pemfile.pem"
        pemPathServer = CONF_HOME + "pemfileServer.pem"
        
        if (awstriggerdataimport.lower() == 'true' and splunkid.strip().lower() != 'awsadmin' and splunkid.strip().lower() != 'admin' and splunkid.strip().lower() != 'saviynt' and connection1.strip().lower() != 'aws' and connection.strip().lower() != 'aws' and systemname.strip().lower() != 'aws'):
            logger.info("awstriggerdataimport is true")
            
        #Validate the app access                 
            OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,gatewayusername,gatewaysavpd,oAuthPemServer)
            authorization = "Bearer "+ OAUTH_TOKEN
                        
            validateAppUrl = gatewayserver + '/ws/rest/validateAppAccess'
            json_app_access = requests.post(validateAppUrl, data = {'extuserid':splunkid,'firstname':firstname,'lastname':lastname,'email':email,'phonenumber':phone,'company':connection1,'appType':appType,'customerCode':splunkid,'accountID':AWS_ACCOUNT_ID,'instanceid':instance},headers={'Authorization':authorization},verify=pemPathServer)
            json_app_access_data = json.loads(json_app_access.text)
            logger.info(json_app_access_data)
            
            appValidMessage = json_app_access_data['msg'].lower()
                        
            if appValidMessage.lower().startswith("valid"):
                logger.info("License is valid")

        #Create Saviynt connection if not yet created
            	if(INSTANCESTATUS.lower()=="false"):
                    logger.info("starting the connection")
                    gateway()

                if(INSTANCESTATUS.lower()=="true"):
                    logger.info("Connection was created before.")

        #start Saviynt connection
                    isStarted = "false"
                    newUrl = None
                    reCreateInstanceReason = ""
                    oldInstance = instance
                    isStarted, newUrl = startInstance(gateway_access_key_id,gateway_secret_access_key,gateway_role_arn,gateway_role_session_name,instance)
                    
                    logger.info(isStarted)
                    #Re-establish connection if it was terminated and inform Saviynt
                    if(isStarted.lower()=="terminated" or isStarted.lower()=="notstarted"):
                        instanceStarted = "false"
                        logger.info("re-starting the connection")
                        gateway()
                        
                        if(isStarted.lower() == "terminated"):
                            reCreateInstanceReason = "The instance was terminated."
                        elif(isStarted.lower() == "notstarted"):
                            reCreateInstanceReason == "The Instance could not be started."
                        
                        if(instanceStarted.lower()=="true"):
                            logger.info("New Connection is created.")
                            isStarted, newUrl = startInstance(gateway_access_key_id,gateway_secret_access_key,gateway_role_arn,gateway_role_session_name,instance)
                   
                            if(isStarted.lower() != "true"):
                                reCreateInstanceReason = reCreateInstanceReason + " Retried and could not start the new instance."
                                
                        else:
                            reCreateInstanceReason = reCreateInstanceReason + " Retried and could not create new instance."
                            
                        oldInstance = "Old Instance: "+oldInstance + ", New Instance: " + instance
                    elif (isStarted.strip().lower() != "true"): 
                        reCreateInstanceReason = isStarted
                    
                    if (reCreateInstanceReason != ""):
                        sendRecreateInstanceEmail(reCreateInstanceReason,oldInstance,splunkid,firstname,lastname,email,phone,connection)
                        logger.info("email sent")
                                   
                    if(isStarted.lower()=="true"):
                        if(newUrl is not None):
                            gatewayurl = newUrl
                            logger.info("The url used is : "+ newUrl)
                             
        #List of URLs
                        connURL = gatewayurl+'/restful/testConnection'
                        importURL = gatewayurl+'/restful/importData'
                        checkStatusURL = gatewayurl+'/restful/checkImportStatus'
                        forceCompleteURL = gatewayurl+'/restful/forceComplete'
                        runAllControlsURL = gatewayurl+'/restful/runAnalyticsControls'
                        checkJobStatusURL = gatewayurl+'/restful/checkJobStatus'
                        fetchControlListURL = gatewayurl+'/restful/fetchControlList'
                        fetchControlDetailsURL = gatewayurl+'/restful/fetchControlDetails'

                        logger.info("Test connURL is:"+connURL)
                        logger.info("importURL is:"+importURL)
                        logger.info("checkStatusURL is:"+checkStatusURL)
                        logger.info("forceCompleteURL is:"+forceCompleteURL)
                        logger.info("runAllControlsURL is:"+runAllControlsURL)
                        logger.info("checkJobStatusURL is:"+checkJobStatusURL)
                        logger.info("fetchControlListURL is:"+fetchControlListURL)
                        logger.info("fetchControlDetailsURL is:"+fetchControlDetailsURL)
                        
        #Import Data Parameters
                        fullorincremental = 'full'
                        accountsoraccess ='accounts'
                        accountsoraccess1 ='access'
                        CREATEUSERS = 'Yes'

        #Run all controls parameters
                        jobgroup = 'Analytics'
                        jobname = 'AnalyticsJob'
                        analyticsCategories = '###ALL###'

        #Check Job Status parameters
                        jobgroup1 = 'Analytics'
                        jobname1 = 'AnalyticsJob'
            
        #Test connection
                        logger.info("Test Connection URL is: "+connURL)
                        logger.info("Testing connection")
                        testConnection = False
                        minutes = 0
                        limitForTimer = 10
                        CONNSTATUS = "Import Failed"
                        json_conn = None
                        while(minutes < limitForTimer):
                            minutes = minutes + 1
                            try:
                            	connectionDescription = "First Name : " + firstname + " Last Name : " + lastname + " Email :" + email + " Phone : " + phone
                                OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                authorization = "Bearer "+ OAUTH_TOKEN
                                if(cloudenabled=="true"):
                                    json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'AWS_STACK_ROLE_NAME':aws_stack_role_name,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
                                else:
                                    json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'AWS_STACK_ROLE_NAME':aws_stack_role_name,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
                                json_conn_data = json.loads(json_conn.text)
                                logger.info(json_conn_data)
                                CONNSTATUS = json_conn_data['msg']
                                if(CONNSTATUS.lower()!='connection successful'):
                                    logger.info("Connection Failed...Trying again")
                                    sleep(10)
                                    OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                    authorization = "Bearer "+ OAUTH_TOKEN          
                                    if(cloudenabled=="true"):
                                        json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'AWS_STACK_ROLE_NAME':aws_stack_role_name,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
                                    else:
                                        json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'AWS_STACK_ROLE_NAME':aws_stack_role_name,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
                                    json_conn_data = json.loads(json_conn.text)
                                    logger.info(json_conn_data)
                                    CONNSTATUS = json_conn_data['msg']
                                testConnection = True
                                break
                            except ConnectionError, ce:
                                logger.info(ce)
                                CONNSTATUS = "Connection Failed"
                                logger.info("Trying to connect to the webservice")
                            except ValueError, ve:
                                logger.info(ve)
                                logger.info("Incorrect credentials")
                                CONNSTATUS = "Connection Failed"
                                return_message = "Import failed. Please check your internet connection and/or AWS credentials and try again. If problem persists contact technical support at 'splunksupport@saviynt.com'."
                                break
                            except Exception, ex:
                                logger.info("Exception caught")
                                logger.info(ex)
                                CONNSTATUS = "Connection Failed"
                                return_message = "Import failed. Please check your internet connection and/or AWS credentials and try again. If problem persists contact technical support at 'splunksupport@saviynt.com'."
                                break
                            sleep(120)
                        if(minutes <= limitForTimer and testConnection):              
                            json_conn_data = json.loads(json_conn.text)
                            CONNSTATUS = json_conn_data['msg'].lower()
                            logger.info(json_conn_data)
                            logger.info(json_conn_data['msg'])
                            
                            if(CONNSTATUS is not None and CONNSTATUS != "" and CONNSTATUS.strip().lower()=='connection successful'):
                                logger.info("Connection successful. Starting accounts Import.")
                                CONNSTATUS = "Connection Failed"
           #Import Accounts                        
                                OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                authorization = "Bearer "+ OAUTH_TOKEN
                                if(cloudenabled=="true"):
                                    json_import = requests.post(importURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'fullorincremental':fullorincremental,'accountsoraccess':accountsoraccess,'CREATEUSERS':CREATEUSERS},headers={'Authorization':authorization},verify=pemPath)
                                else:
                                    json_import = requests.post(importURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'fullorincremental':fullorincremental,'accountsoraccess':accountsoraccess,'CREATEUSERS':CREATEUSERS},headers={'Authorization':authorization},verify=pemPath)
                                json_import_data = json.loads(json_import.text)
                                logger.info(json_import_data)
                                logger.info(json_import_data['msg'])

                                status = 'NOT STARTED'
                                count = 0
                                while (status.lower()=='not started' or status.lower()=='in-progress'):
                                    if count==0:
                                        time.sleep(60)
                                        count += 1
                                    OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                    authorization = "Bearer "+ OAUTH_TOKEN
                                    json_status = requests.post(checkStatusURL,headers={'Authorization':authorization},verify=pemPath)
                                    json_status_data = json.loads(json_status.text)
                                    logger.info(json_status_data)
                                    status = json_status_data['importStatus']
                                    time.sleep(30)
                                    logger.info(status)

        #Import Access
                                logger.info(status)
                                if(status.lower()=='completed'):  
                                    logger.info("Status is completed. Starting access Import")
                                    OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                    logger.info("OAUTH_TOKEN=%s" % OAUTH_TOKEN)
                                    authorization = "Bearer "+ OAUTH_TOKEN
                                    if(cloudenabled=="true"):
                                        json_access_import = requests.post(importURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'fullorincremental':fullorincremental,'accountsoraccess':accountsoraccess1,'CREATEUSERS':CREATEUSERS},headers={'Authorization':authorization},verify=pemPath)
                                    else:
                                        json_access_import = requests.post(importURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'fullorincremental':fullorincremental,'accountsoraccess':accountsoraccess1,'CREATEUSERS':CREATEUSERS},headers={'Authorization':authorization},verify=pemPath)
                                    json_access_import_data = json.loads(json_access_import.text)
                                    logger.info(json_access_import_data)
                                    logger.info(json_access_import_data['msg'])

                                    status = 'NOT STARTED'
                                    count = 0
                                    while (status.lower()=='not started' or status.lower()=='in-progress'):
                                        if count==0:
                                            time.sleep(60)
                                            count += 1
                                        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
                                        logger.info("OAUTH_TOKEN=%s" % OAUTH_TOKEN)
                                        authorization = "Bearer "+ OAUTH_TOKEN
                                        json_status = requests.post(checkStatusURL,headers={'Authorization':authorization},verify=pemPath)
                                        json_status_data = json.loads(json_status.text)
                                        logger.info(json_status_data)
                                        status = json_status_data['importStatus']
                                        time.sleep(90)
                                        logger.info(status)

        #Run all Controls
                                    status = "completed"
                                    logger.info(status)
                                    if(status.lower()=='completed'):
                                        logger.info("Status is completed. Running all controls")
                                        pullData(connection,gatewayurl,OAUTH_TOKEN,oAuthPemInstance)
                                        logger.info("Done pulling data")
                                        return_message = "Import Complete"
                                        CONNSTATUS = "Connection Successful"
                                    else:
                                        return_message = "Import Failed"
                            else:
                                logger.info("Could not connect.")
                                CONNSTATUS = "Connection Failed"
                                return_message = "Import Failed"
                    else:
                        logger.info("Could not connect")
                        return_message = "Import Failed"
                            
                else:
                    logger.info("Could not connect to the Server")
                    return_message = "Import Failed"
            else:
                logger.info("App verification failed")
                logger.info(json_app_access_data['msg'])
            
        else:
            logger.info("Non permissible values of splunk id or connection")

        importSuccessFlag = True
    else:
        logger.info("Other process is running")
        return_message = "Other Process is running. Please wait."
except Exception, ex:
    logger.exception(ex)
    return_message = "Import Failed."
    importSuccessFlag = False
finally:
    #Stop the connection with Saviynt and save modified user's connection details
    try:
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayurl,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemInstance)
        logger.info(OAUTH_TOKEN)
        authorization = "Bearer "+ OAUTH_TOKEN
                    
        fetchHistoryUrl = gatewayurl + '/ws/rest/fetchhistorydata'
        logger.info(fetchHistoryUrl)
        json_fetch_history = requests.post(fetchHistoryUrl,headers={'Authorization':authorization},verify=pemPath)
        logger.info(json_fetch_history)
        
        json_fetch_history_data = json.loads(json_fetch_history.text)
        
        fetch_data = json_fetch_history.text
        fetch_data = fetch_data.replace("'","")
        
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,gatewayusername,gatewaysavpd,oAuthPemServer)
        authorization = "Bearer "+ OAUTH_TOKEN
                    
        saveHistoryUrl = gatewayserver + '/ws/rest/savehistorydata'
        json_save_history = requests.post(saveHistoryUrl, data = {'extuserid':splunkid,'data':fetch_data,'appname':'SPLUNK-APP','controlrun':'SPLUNK-CONTROLS'},headers={'Authorization':authorization},verify=pemPathServer)
        
    except Exception, ex:
        logger.info(ex)
        
    try:
        if (instance is not None and instance.strip() != ""):
            isStopped = stopInstance(gateway_access_key_id,gateway_secret_access_key,gateway_role_arn,gateway_role_session_name,instance)
            if(isStopped):
                logger.info("Stopping the connection")
            else:
                logger.info("Error stopping")
        
    except Exception, ex:
        logger.info(ex)
    
    try:
        if(isOtherProcessRunning == False):
            IMPORTSTATUS = "false"
            if(importSuccessFlag):
                logger.info("Writing modified data to testconn")
                writeToTestConn()
            else:
                if(len(testConnBackupData) > 0):
                    logger.info("Writing backup data to testconn")
                    cloudenabled = testConnBackupData['cloudenabled']
                    connection1 = testConnBackupData['connection']
                    if 'AWS_ACCESS_KEY' in testConnBackupData:
                        AWS_ACCESS_KEY = testConnBackupData['AWS_ACCESS_KEY']
                    if 'AWS_ACCESS_SECRET_savpd' in testConnBackupData:
                        AWS_ACCESS_SECRET_savpd = testConnBackupData['AWS_ACCESS_SECRET_savpd']
                    AWS_ACCOUNT_ID = testConnBackupData['AWS_ACCOUNT_ID']
                    CROSS_ACCOUNT_ROLE_ARN = testConnBackupData['CROSS_ACCOUNT_ROLE_ARN']
                    CONNSTATUS = testConnBackupData['CONNSTATUS']
                    INSTANCESTATUS = testConnBackupData['INSTANCESTATUS']
                    IMPORTSTATUS = "false"
                    ISACTIVE = testConnBackupData['ISACTIVE']
                    IS_ACCOUNT_ACTIVATED = testConnBackupData['IS_ACCOUNT_ACTIVATED']
                    splunkid = testConnBackupData['SPLUNK_ID']
                    firstname = testConnBackupData['FIRST_NAME']
                    lastname = testConnBackupData['LAST_NAME']
                    email = testConnBackupData['EMAIL']
                    phone = testConnBackupData['PHONE']
                    timestamp = testConnBackupData['timestamp']
                    OAUTH_TOKEN = testConnBackupData['OAUTH_TOKEN']
                    writeToTestConn()
    except Exception, ex:
        logger.info(ex)
    logger.info("Import Result:"+ return_message)
    print "Result:"    
    print return_message
    logger.info("Response sent")

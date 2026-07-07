import httplib
from urlparse import urlparse
import logging, logging.handlers
import sys,os,splunk.Intersplunk
import csv
import time
import json
import requests
import base64
from time import sleep
from time import gmtime, strftime
from requests.exceptions import ConnectionError

from createLogs import setup_logging
from oAuthToken import validateOrGetOAuthToken
from validateConnection import setMessage
from validateConnection import getMessage

logger = setup_logging()

'''
    This is the primary step - to verify the user credentials.
'''
def testConn():
    global ISACTIVE
    global OAUTH_TOKEN
    global CONNSTATUS
    global IS_ACCOUNT_ACTIVATED
    CONNSTATUS = "Connection Failed"
    try:
        logger.info("Test Connection URL is: "+connURL)
        connectionDescription = "First Name = " + firstname +" Last Name =" + lastname + " Email =" + email + " Phone = " + phone;
        logger.info("conn desc"+connectionDescription)
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,gatewayusername,gatewaysavpd,oAuthPemServer)
        authorization = "Bearer "+ OAUTH_TOKEN
        if(cloudenabled=="true"):
            logger.info("Connection: "+connection)
            json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
        else:
            logger.info("Connection : "+connection)
            json_conn = requests.post(connURL, data={'connectionName':connection,'connectionDescription':connectionDescription,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
        json_conn_data = json.loads(json_conn.text)
        logger.info("Printing test conn json data......")
        logger.info(json_conn_data)
        logger.info(json_conn_data['msg'])

        if(json_conn_data['msg'].lower()!='connection successful'):
            logger.info("Test Connection Failed...Trying again")
            sleep(10)
            OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,gatewayusername,gatewaysavpd,oAuthPemServer)
            authorization = "Bearer "+ OAUTH_TOKEN
            
            if(cloudenabled=="true"):
                logger.info("Connection : "+connection)
                json_conn = requests.post(connURL, data = {'connectionName':connection,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'connectionDescription':connectionDescription,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
            else:
                logger.info("Connection : "+connection)
                json_conn = requests.post(connURL, data={'connectionName':connection,'connectionDescription':connectionDescription,'connectiontype':connectiontype,'systemname':systemname,'AWS_ACCESS_KEY':AWS_ACCESS_KEY,'AWS_ACCESS_SECRET_PASSWORD':AWS_ACCESS_SECRET_savpd,'AWS_ACCOUNT_ID':AWS_ACCOUNT_ID,'CROSS_ACCOUNT_ROLE_ARN':CROSS_ACCOUNT_ROLE_ARN,'saveconnection':saveconnection},headers={'Authorization':authorization},verify=pemPath)
            
       	    json_conn_data = json.loads(json_conn.text)
       	    logger.info("Printing test conn json data......")
       	    logger.info(json_conn_data)
            logger.info(json_conn_data['msg'])
            
        if(json_conn_data['msg'].lower()=='connection successful'):
            logger.info("Connection successful.")
            ISACTIVE = "true"
            if IS_ACCOUNT_ACTIVATED == "false" :
                IS_ACCOUNT_ACTIVATED = "true"
        else:
            ISACTIVE = "false"
            logger.info("Connection failed.")
        CONNSTATUS = json_conn_data['msg']
    except ConnectionError, ce:
        logger.info(ce)
        CONNSTATUS = "Connection failed. Please check your internet connection and/or AWS credentials and try again. If problem persists contact technical support at 'splunksupport@saviynt.com'." 
    except Exception, ex:
        logger.exception(ex)
        raise
 
'''
    Save the connection details of the customer in a file.
''' 
def writeToTestConn():
    #write into testconn file
    conf_write = None
    conf_write_file_path = STATIC_HOME + "testconn.txt"
    logger.info("Config file is:"+conf_write_file_path)
    try:
        if(testConnRead):
            logger.info("Writing into textconn.txt file")
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
    Variables declared
'''
return_message = "Connection Failed"
testConnBackupData = {}
isOtherProcessRunning = True
importSuccessFlag = False
saveconnection = 'Y'
oAuthPemServer = "server"
oAuthPemInstance = "instance"

SPLUNK_HOME = ""
CONF_HOME = ""
STATIC_HOME = ""
connURL = ""
    
externalConfigRead = False
awstriggerdataimport = ''
connectiontype = ''
systemname = ''
gatewayserver = ''
gatewayusername = ''
gatewaysavpdenc = ''
gatewaysavpd = ''
gatewayurl = ''
savusername = ''
savsavpd = ''
gateway_access_key_id = ''
gateway_secret_access_key = ''
gateway_role_session_name = ''
gateway_role_arn =''
instance = None

testConnRead = False
cloudenabled=''
connection = ''
connection1 = ''
AWS_ACCESS_KEY = ''
AWS_ACCESS_SECRET_savpd = ''
AWS_ACCOUNT_ID = ''
CROSS_ACCOUNT_ROLE_ARN = ''
CONNSTATUS = ''
INSTANCESTATUS = ''
IMPORTSTATUS = "false"
ISACTIVE = "false"
IS_ACCOUNT_ACTIVATED = ''
splunkid = ''
firstname = ''
lastname = ''
email = ''
phone = ''
timestamp = ''
OAUTH_TOKEN = None

'''
    Test Connection
'''
try:
    #Paths
    SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
    CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
    STATIC_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/static/"
    logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
    logger.info("CONF_HOME is:"+CONF_HOME)
    logger.info("STATIC_HOME is:"+STATIC_HOME)
     
    #Reading the testconn file to get the stored user details
    logger.info("Reading the testconn file")
    conn_read_file_path = STATIC_HOME + "testconn.txt"
    logger.info("Connection file is:"+conn_read_file_path)
    conn_read = open(conn_read_file_path, 'r')
    value = ''
    for line in conn_read:
        conn,value = line.split(":=:")
        if (conn.strip().lower() == 'cloudenabled'):
            cloudenabled = value.strip().lower()
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
            logger.info("Splunk id value is: "+splunkid)
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
    
    #Connection Parameters got from the User Interface
    if(cloudenabled=="true"):
        connection1=sys.argv[1]
        connection = connection1.replace(" ","")
        AWS_ACCOUNT_ID=sys.argv[2]
        CROSS_ACCOUNT_ROLE_ARN=sys.argv[3]
        firstname=sys.argv[4]
        lastname=sys.argv[5]
        email=sys.argv[6]
        phone=sys.argv[7]
        splunkid = sys.argv[8]
    else:
        connection1=sys.argv[1]
        connection = connection1.replace(" ","")
        AWS_ACCESS_KEY=sys.argv[2]
        AWS_ACCESS_SECRET_savpd=sys.argv[3]
        AWS_ACCOUNT_ID=sys.argv[4]
        CROSS_ACCOUNT_ROLE_ARN=sys.argv[5]
        firstname=sys.argv[6]
        lastname=sys.argv[7]
        email=sys.argv[8]
        phone=sys.argv[9]
        splunkid = sys.argv[10]
        testConnBackupData['AWS_ACCESS_KEY']=AWS_ACCESS_KEY
        testConnBackupData['AWS_ACCESS_SECRET_savpd']=AWS_ACCESS_SECRET_savpd
    
    #Maintain backup of the user details
    testConnBackupData['connection']=connection1
    testConnBackupData['AWS_ACCOUNT_ID']=AWS_ACCOUNT_ID
    testConnBackupData['CROSS_ACCOUNT_ROLE_ARN']=CROSS_ACCOUNT_ROLE_ARN
    testConnBackupData['SPLUNK_ID']=splunkid
    testConnBackupData['FIRST_NAME']=firstname
    testConnBackupData['LAST_NAME']=lastname
    testConnBackupData['EMAIL']=email
    testConnBackupData['PHONE']=phone
    
    #Ensure that no other job is running
    if (IMPORTSTATUS.lower() == "false"):
        
        isOtherProcessRunning = False
        #update the import status
        logger.info("write to test conn file")
        IMPORTSTATUS = "saveandtest"
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
            if (conf.strip().lower() == 'instance'):
                instance = value.strip()
            if (conf.strip().lower() == 'servername'):
                gatewayusername = value.strip()
            if (conf.strip().lower() == 'servermessage'):
                gatewaysavpdenc = value.strip()
                gatewaysavpd = getMessage(gatewaysavpdenc)
            if (conf.strip().lower() == 'savname'):
                savusername = value.strip()
            if (conf.strip().lower() == 'savmessage'):
                savsavpdenc = value.strip()
                if(savsavpdenc.lower()!='default'):
                    savsavpd = getMessage(savsavpdenc)
                else:
                    savsavpd = savsavpdenc
        externalConfigRead = True
        conf_read.close()

        pemPath = CONF_HOME + "pemfileServer.pem"
        
        #Test connection
        if(timestamp.strip() == "" or timestamp.strip().lower() == "default"):
            timestamp = strftime("%Y%m%d%H%M%S", gmtime())
        systemname = connection + timestamp
        
        connection = systemname
        
        results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

        CONNSTATUS = "Connection Failed"
        connURL = gatewayserver+'/restful/testConnection'
        logger.info("Test connURL is:"+connURL)
        
        if (splunkid.strip().lower() != 'awsadmin' and splunkid.strip().lower() != 'admin' and splunkid.strip().lower() != 'saviynt' and connection1.strip().lower() != 'aws' and connection.strip().lower() != 'aws' and systemname.strip().lower() != 'aws'):
            testConn()
        else:
            logger.info("Non permissible value of splunkid or connection")
        return_message = CONNSTATUS
        
        logger.info(return_message)
        importSuccessFlag = True
        
    else:
        logger.info("Other process is running")
        return_message = "Other Process is running."
except Exception, ex:
    logger.exception(ex)
    importSuccessFlag = False
finally:
    #Store updated user data
    if(isOtherProcessRunning == False):
        try:
            logger.info("Testconn back up data")
            logger.info(testConnBackupData)
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
            logger.info("Unable to write to testconn")
    print "Result:"    
    print return_message
    logger.info("Response sent")

import logging
import sys,os
import splunk.Intersplunk
import json
import requests

logger = logging.getLogger('splunk.saviynt')

'''
    Store the token
'''
def writeOAuthToken(token):
    logger.info("Write token to testconn file")
    global OAUTH_TOKEN
    OAUTH_TOKEN = token
    writeToTestConn()
    
'''
    Store token with the user's connection data into testconn file
'''
def writeToTestConn():
    conf_write = None
    conf_write_file_path = STATIC_HOME + "testconn.txt"
    logger.info("Config file is:"+conf_write_file_path)
    try:
        if(testConnRead):
            logger.info("Writing into textconn.txt file")
            conf_write = open(conf_write_file_path, "w")
            conf_write.truncate()
            conf_write.write("cloudenabled:=:%s\n" % cloudenabled)
            conf_write.write("connection:=:%s\n" % connection)
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
            conf_write.write("SPLUNK_ID:=:%s\n" % SPLUNK_ID)
            conf_write.write("FIRST_NAME:=:%s\n" % firstname)
            conf_write.write("LAST_NAME:=:%s\n" % lastname)
            conf_write.write("EMAIL:=:%s\n" % email)
            conf_write.write("PHONE:=:%s\n" % phone)
            conf_write.write("timestamp:=:%s\n" % timestamp)
            conf_write.write("OAUTH_TOKEN:=:%s\n" % OAUTH_TOKEN)
            logger.info("Written into testconn text file.") 
    except Exception, ex:
        logger.info(ex)
    finally:
        if conf_write is not None:
            conf_write.close()
            logger.info("testconn file closed after writing")
            
'''
    Reading the testconn file to get the user's connection data
'''            
def readTestConnData():
    conn_read = None
    global testConnRead
    global cloudenabled
    global connection
    global AWS_ACCESS_KEY
    global AWS_ACCESS_SECRET_savpd
    global AWS_ACCOUNT_ID
    global CROSS_ACCOUNT_ROLE_ARN
    global CONNSTATUS
    global INSTANCESTATUS
    global IMPORTSTATUS
    global ISACTIVE
    global IS_ACCOUNT_ACTIVATED
    global gatewayurl
    global SPLUNK_ID
    global firstname
    global lastname
    global email
    global phone
    global timestamp
    global OAUTH_TOKEN
    try:
        logger.info("Reading the testconn file")
        conn_read_file_path = STATIC_HOME + "testconn.txt"
        logger.info("Connection file is:"+conn_read_file_path)
        conn_read = open(conn_read_file_path, 'r')
        value = ''
        for line in conn_read:
            conn,value = line.split(":=:")
            if (conn.strip().lower() == 'cloudenabled'):
                cloudenabled = value.strip()
            if (conn.strip().lower() == 'connection'):
                connection = value.strip()
            if (conn.strip() == 'AWS_ACCESS_KEY'):
                AWS_ACCESS_KEY = value.strip()
            if (conn.strip() == 'AWS_ACCESS_SECRET_savpd'):
                AWS_ACCESS_SECRET_savpd = value.strip()
            if (conn.strip() == 'AWS_ACCOUNT_ID'):
                AWS_ACCOUNT_ID = value.strip()
            if (conn.strip() == 'CROSS_ACCOUNT_ROLE_ARN'):
                CROSS_ACCOUNT_ROLE_ARN = value.strip()
            if (conn.strip() == 'CONNSTATUS'):
                CONNSTATUS = value.strip()
            if (conn.strip() == 'INSTANCESTATUS'):
                INSTANCESTATUS = value.strip()
            if (conn.strip() == 'IMPORTSTATUS'):
                IMPORTSTATUS = value.strip()
            if (conn.strip() == 'ISACTIVE'):
                ISACTIVE = value.strip()
            if (conn.strip() == 'IS_ACCOUNT_ACTIVATED'):
                IS_ACCOUNT_ACTIVATED = value.strip()
            if (conn.strip() == 'SPLUNK_ID'):
                SPLUNK_ID = value.strip()
            if (conn.strip() == 'FIRST_NAME'):
                firstname = value.strip()
            if (conn.strip() == 'LAST_NAME'):
                lastname = value.strip()
            if (conn.strip() == 'EMAIL'):
                email = value.strip()
            if (conn.strip() == 'PHONE'):
                phone = value.strip()
            if (conn.strip() == 'timestamp'):
                timestamp = value.strip()
            if (conn.strip() == 'OAUTH_TOKEN'):
                OAUTH_TOKEN = value.strip()
        testConnRead = True
    except Exception, ex:
        logger.info(ex)
    finally:
        if conn_read is not None:
            conn_read.close()
            logger.info("testconn file closed after reading")

'''
    Variables declared
''' 
testConnRead = False
cloudenabled = ''
connection = ''
AWS_ACCESS_KEY = ''
AWS_ACCESS_SECRET_savpd = ''
AWS_ACCOUNT_ID = ''
CROSS_ACCOUNT_ROLE_ARN = ''
CONNSTATUS = ''
INSTANCESTATUS = ''
IMPORTSTATUS = "false"
ISACTIVE = "false"
IS_ACCOUNT_ACTIVATED = ''
SPLUNK_ID = ''
gatewayurl = ''
firstname = ''
lastname = ''
email = ''
phone = ''
timestamp = '' 
OAUTH_TOKEN = None
STATIC_HOME = ""

'''
    Validate new token or get a new token
'''

def validateOrGetOAuthToken(url,token,username,savpd,pemType):
    try:
        global STATIC_HOME
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        STATIC_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/static/"
        logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
        logger.info("CONF_HOME is:"+CONF_HOME)
        logger.info("STATIC_HOME is:"+STATIC_HOME)
        if(pemType.strip().lower() == "server"):
            pemPath = CONF_HOME + "pemfileServer.pem"
        elif (pemType.strip().lower() == "instance"):
            pemPath = CONF_HOME + "pemfile.pem"

        logger.info("got token from testconn file")
        logger.info(token)
        if(token is not None and token.strip() != ""):
            isValid = validateOAuthToken(url,token,pemPath)

            if(isValid):
                return token
            else: 
                token = getOAuthToken(url, username, savpd, pemPath)
                return token
        else:
            token = getOAuthToken(url, username, savpd, pemPath)
            return token
        return None
    except Exception,ex:
       logger.info(ex)
       raise

'''
    Get new oAuth token
'''       
def getOAuthToken(url, username, savpd, pemPath):
    try:
        getOAuthUrl = url + "/restful/getToken/"
        logger.info("Url to get token: "+getOAuthUrl)
        getOAuthResponse = requests.post(getOAuthUrl,data={'username':username,'password':savpd},verify=pemPath)
        getOAuthResponse_data = json.loads(getOAuthResponse.text)
        logger.info(getOAuthResponse_data)
        
        if getOAuthResponse_data['RESULT'] == 'OK':
            token = getOAuthResponse_data['TOKEN']
            readTestConnData()
            writeOAuthToken(token)
            return token
        else:
            return None
    except Exception,ex:
        logger.info(ex)
        raise
    
'''
    Check the validity of the stored token
'''
def validateOAuthToken(url,token,pemPath):
    try:
        validateOAuthUrl = url + "/restful/validateToken/"
        logger.info("Validate token url :"+validateOAuthUrl)
        
        validateOAuthResponse = requests.post(validateOAuthUrl,data={'token':token},verify=pemPath)
        logger.info("Validate token response: ")
        logger.info((validateOAuthResponse.text))
        
        if validateOAuthResponse.text == "TOKEN is VALID":
            return True
        else:
            return False
    except Exception,ex:
        logger.info(ex)
        raise

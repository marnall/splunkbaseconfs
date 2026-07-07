import logging
import sys,os
import json
import requests
from validateConnection import getMessage
from oAuthToken import validateOrGetOAuthToken
logger = logging.getLogger('splunk.saviynt')

'''
    Send email to Saviynt.
'''

def sendEmails(messageBody,subject,gatewayserver,Savusername,Savsavpd):

    OAUTH_TOKEN = None
    try:
        logger.info(subject)
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        logger.info("CONF_HOME:"+CONF_HOME)

        pemPath = CONF_HOME + "pemfileServer.pem"
        oAuthPemServer = "server"
        
        sendTo = "splunksupport@saviynt.com"
        sendFrom = "saviyntsmtp@gmail.com"
         
        OAUTH_TOKEN = validateOrGetOAuthToken(gatewayserver,OAUTH_TOKEN,Savusername,Savsavpd,oAuthPemServer)
        authorization = "Bearer "+ OAUTH_TOKEN
        logger.info("get oauth token")
        logger.info(OAUTH_TOKEN)
        
        sendEmailUrl = gatewayserver + '/ws/rest/sendEmail'
        json_sendEmail = requests.post(sendEmailUrl, data = {'from':sendFrom,'to':sendTo,'body':messageBody,'subject':subject},headers={'Authorization':authorization},verify=pemPath)
        json_sendEmail_data = json.loads(json_sendEmail.text)
        logger.info(json_sendEmail_data)
        sendEmailResponse = json_sendEmail_data['msg']
        
        if sendEmailResponse.strip().lower() == "successful" :
            return True
        return False
    except Exception, ex:
        logger.info(ex)
        return False

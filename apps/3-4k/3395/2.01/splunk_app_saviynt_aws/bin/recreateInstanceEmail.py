import logging
import sys,os
from sendEmail import sendEmails
from validateConnection import getMessage

logger = logging.getLogger('splunk.saviynt')
return_message = "Error occurred. Could not send request to Saviynt."
conf_read = None

'''
    Send email to Saviynt.
    If unable to connect, send email.
'''

def sendRecreateInstanceEmail(reason,instanceValue,splunkid,firstName,lastName,email,phone,company):
    try:
        logger.info(reason)
        subject = "AWS Instance Issue - Saviynt for AWS Splunk (Free Version)"
        
        SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
        CONF_HOME = SPLUNK_HOME + "/etc/apps/splunk_app_saviynt_aws/default/"
        logger.info("SPLUNK_HOME is:"+SPLUNK_HOME)
        logger.info("CONF_HOME is:"+CONF_HOME)
         
        #Reading the external config file
        logger.info("Reading the external config file")
        instance = ''
        conf_read_file_path = CONF_HOME + "externalconfig.txt"
        logger.info("Config file is:"+conf_read_file_path)
        conf_read = open(conf_read_file_path, 'r')
        for line in conf_read:
            conf,value = line.split(":=:")
            if (conf.strip().lower() == 'instance'):
                instance = value.strip()
            if (conf.strip().lower() == 'serverurl'):
                serverurl = value.strip()
            if (conf.strip().lower() == 'servername'):
                serverusername = value.strip()
            if (conf.strip().lower() == 'servermessage'):
                serversavpd = value.strip()
                getpswd = getMessage(serversavpd)
        conf_read.close()
         
        html="""
        <div class="form-body2">
                <table>
                    <tr>
                        <td>Splunk Id:
                        </td>
                        <td>
        """ + splunkid + """                   
                            </td>
                    </tr>
                    
                    <tr>
                        <td>First Name:
                        </td>
                        <td>
        """ + firstName + """                   
                            </td>
                    </tr>
                    
                    <tr>
                        <td>
                            Last Name:
                        </td>
                        
                            <td >
        """ + lastName + """
                           
                            </td>
                            
                    </tr>
                    
                        
                    <tr>
                        <td>
                            Email Address:
                        </td>
                        
                            <td >
        """ + email + """                    
                            </td>
                            
                    </tr>

                    <tr>
                        <td>
                            Phone Number
                        </td>
                        <td>
        """ + phone + """
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Company Name:
                        </td>
                        <td>
        """ + company + """
                        </td>
                    </tr>

                    <tr>
                        <td>
                            Instance Id:
                        </td>
        """ + instanceValue + """
                        </td>
                    </tr>
                    <tr>
                        <td>
                            Reason:
                        </td>
                        <td>
        """ + reason + """
                        </td>
                    </tr>
        </table>
        </div>       
        """
        
        response = sendEmails(html,subject,serverurl,serverusername,getpswd)
        logger.info(response)
        
        if response:
            return_message = "Your request has been sent to Saviynt. Your query will be answered within 24 hours."
        else:
            return_message = "Could not submit your request. Please check your internet connection. If problem persists contact technical support at 'splunksupport@saviynt.com'."
    except Exception, ex:
        logger.info(ex)
        return_message = "Could not submit your request. Please check your internet connection. If problem persists contact technical support at 'splunksupport@saviynt.com'."
    finally:
        try:
            if conf_read is not None:
                conf_read.close()
        except Exception, ex2:
            logger.info(ex2)
        logger.info(return_message)

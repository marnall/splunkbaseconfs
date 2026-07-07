import logging
import sys,os
from createLogs import setup_logging
from sendEmail import sendEmails
from validateConnection import getMessage

logger = setup_logging()
return_message = "Error occurred. Could not send request to Saviynt."
conf_read = None

'''
    Send Email to Saviynt.
    User can ask for new controls.
'''
try:

    firstName = sys.argv[1]
    logger.info(firstName)
    lastName = sys.argv[2]
    logger.info(lastName)
    email = sys.argv[3]
    logger.info(email)
    phone = sys.argv[4]
    logger.info(phone)
    company = sys.argv[5]
    logger.info(company)
    category = sys.argv[6]
    logger.info(category)
    control = sys.argv[7]
    logger.info(control)
    description = sys.argv[8]
    logger.info(description)
    splunkId = sys.argv[9]
    logger.info(splunkId)
    
    subject = "Create new analytics - Saviynt for AWS Splunk (Free Version)"
    
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
    """ + splunkId + """                   
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
                        Phone Number:
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
    """ + instance + """
                    </td>
                </tr>
                <tr>
                    <td>
                        Analytics Category:
                    </td>
                    <td>
    """ + category + """
                    </td>
                </tr>
                <tr>
                    <td>
                        Analytics Name:
                    </td>
                    <td>

    """ + control + """
                    
                    
                    </td>
                
                </tr>
                <tr>
                    <td>
                        Description:
                    </td>
                    <td>
    """ + description + """
                    </td>
                </tr>
         
    </table>
    </div>       
    """

    response = sendEmails(html,subject,serverurl,serverusername,getpswd)
    logger.info(response)
    
    if response:
        return_message = "Your request has been sent to Saviynt. New analytics will be created within 24 hrs and will be available in Splunk after the next Import."
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
    print 'done'
    print return_message
    logger.info(return_message)


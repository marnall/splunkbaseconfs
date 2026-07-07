###############################################################################
###############################################################################
##
##  SENDRESULTS - a splunk email command
##
##  Discovered Intelligence
##  https://discoveredintelligence.ca
##
##  For support contact:
##  support@discoveredintelligence.ca
##
###############################################################################
###############################################################################

import sys, os, string, shutil, socket
import random
import time
import json
import csv
from collections import defaultdict
import splunk.Intersplunk # pylint: disable=F0401
import splunk.entity as entity # pylint: disable=F0401
from splunk.rest import simpleRequest # pylint: disable=F0401
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders, utils
import logging as logger
from io import (BytesIO, TextIOWrapper)

## Create a unique identifier for this invocation
NOWTIME         = time.time()
SALT            = random.randint(0, 100000)
INVOCATION_ID   = str(NOWTIME) + ':' + str(SALT)
INVOCATION_TYPE = "command"

######################################################
##-- Helper function to access the server type
##--
def getServerType(settings):

    sessionKey = settings['sessionKey']
    server_type = ""

    try:
        server_info = entity.getEntity('server', 'info', owner='nobody', sessionKey=sessionKey)
    except Exception as e:
        raise Exception("Could not get server info from splunk. Error: %s" % (str(e)))

    if('instance_type' in server_info):
        server_type = server_info['instance_type']

    return server_type

###############################################################################
#
# Function:   getAlternateCredentials
#
# Descrition: This function calls the Splunk REST API to get the SMTP credentials
#             Using the "show_password" way :(
#
# Arguments:
#    sessionKey - key used to authenticate with Splunk
#
###############################################################################

def getAlternateCredentials(sessionKey):
    try:
        uri = 'admin/alert_actions/email'

        # Need to send a POST with show_password flag set to True to get user/pass
        response, content = simpleRequest(uri, method='POST', postargs={'show_password': True, 'output_mode': 'json'}, sessionKey=sessionKey)

        # invalid server response status check
        if response['status']!='200':
            logger.error('getCredentials - unable to retrieve credentials; check simpleRequest response')
            return None

        # parse credentials from the returned response
        contentJson = json.loads(content)
        userCredentials = contentJson['entry'][0]['content']

        auth_username  = userCredentials.get('auth_username')
        clear_password = userCredentials.get('clear_password')

        # set the user/pass if found
        if (len(auth_username) and len(clear_password)):
            return auth_username, clear_password

    except Exception as e:
        logger.error("Could not get email credentials from splunk, using no credentials. Error: %s" % (str(e)))

    return '', ''

###############################################################################
#
# Function:   getCredentials
#
# Descrition: This function calls the Splunk REST API to get the SMTP credentials
#             Handles pre-8.0.5 and 8.1.1+ methods.
#
# Arguments:
#    sessionKey - key used to authenticate with Splunk
#    namespace - Splunk namespace value for the REST API
#    is_cloud - flag to indicate if Splunk Cloud or not
#
###############################################################################

def getCredentials(sessionKey, namespace, is_cloud):
    if(not is_cloud):
        try:
            # Retreive the email alert action settings
            ent = entity.getEntity('admin/alert_actions', 'email', namespace=namespace, owner='nobody', sessionKey=sessionKey)
            if 'auth_username' in ent and 'clear_password' in ent:
                # This is pre-Splunk changing how the password is stored
                if (not ent['clear_password'].startswith('$1$') and not ent['clear_password'].startswith('$7$')):
                    return ent['auth_username'], ent['clear_password']
                else:
                    # This is the 8.1.1+ way to get the password
                    encrypted_password = ent['clear_password']
                    splunkhome = os.environ.get('SPLUNK_HOME')
                    if splunkhome == None:
                        logger.error('getCredentials - unable to retrieve credentials; SPLUNK_HOME not set')
                        return None
                    # if splunk home has white spaces in path
                    splunkhome='\"' + splunkhome + '\"'
                    if sys.platform == "win32":
                        encr_passwd_env = "\"set \"ENCRYPTED_PASSWORD=" + encrypted_password + "\" "
                        commandparams = ["cmd", "/C", encr_passwd_env, "&&", os.path.join(splunkhome, "bin", "splunk"), "show-decrypted", "--value", "\"\"\""]
                    else:
                        encr_passwd_env = "ENCRYPTED_PASSWORD='" + encrypted_password + "'"
                        commandparams = [encr_passwd_env, os.path.join(splunkhome, "bin", "splunk"), "show-decrypted", "--value", "''"]
                    command = ' '.join(commandparams)
                    stream = os.popen(command)
                    clear_password = stream.read()
                    # the decrypted password is appended with a '\n'
                    if len(clear_password) >= 1:
                        clear_password = clear_password[:-1]
                    return ent['auth_username'], clear_password
            elif 'auth_username' not in ent:
                # This is the weird 8.0.5-8.1.0 way of getting credentials
                username, password = getAlternateCredentials(sessionKey)
                return username, password
        except Exception as e:
            logger.error("Could not get email credentials from splunk, using no credentials. Error: %s" % (str(e)))

    return '', ''

###############################################################################
#
# Function:   getEmailAlertActions
#
# Descrition: This function calls the Splunk REST API to get the various alert
#             email configuration settings needed to send SMTP messages in the
#             way that Splunk does
#
# Arguments:
#    argvals  - hash of various arguments passed into the search.
#    settings - hash of various Splunk configuration settings.
#    is_cloud - flag to indicate if Splunk Cloud or not
#
###############################################################################

def getEmailAlertActions(argvals, settings, is_cloud):
    try:
        namespace  = settings.get("namespace", None)
        sessionKey = settings['sessionKey']
        ent = entity.getEntity('admin/alert_actions', 'email', namespace=namespace, owner='nobody', sessionKey=sessionKey)

        argvals['server'] = ent['mailserver']
        argvals['sender'] = ent['from']
        argvals['use_ssl'] = ent['use_ssl']
        argvals['use_tls'] = ent['use_tls']

        namespace  = settings.get("namespace", None)
        username, password = getCredentials(settings['sessionKey'], namespace, is_cloud)
        argvals['username'] = username
        argvals['password'] = password

    except Exception as e:
        logger.error('invocation_id=%s invocation_type="%s" msg="Could not get email alert actions from splunk" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,str(e)))
        raise

###############################################################################
#
# Function:   sendemail
#
# Descrition: This function sends a MIME encoded e-mail message using Splunk SMTP
#			  Settings.
#
# Arguments:
#    recipient - maps the the field 'email_to' in the event returned by Search.
#    bcc - adds additional email addresses to the message envelope.
#    subject - maps to the field 'subject' in the event returned by Search.
#    body - maps the field 'message' in the event returned by Search.
#    argvals - hash of various arguments needed to configure the SMTP connection etc.
#
###############################################################################

def sendemail(recipient, bcc, subject, body, argvals, csvdata=None):

    try:
        server = getarg(argvals, "server", "localhost")
        sender = getarg(argvals, "sender", "splunk")
        use_ssl = toBool(getarg(argvals, "use_ssl"  , "false"))
        use_tls = toBool(getarg(argvals, "use_tls"  , "false"))
        username = getarg(argvals, "username"  , "")
        password = getarg(argvals, "password"  , "")

        # make sure the sender is a valid email address
        if (sender.find("@") == -1):
            sender = sender + '@' + socket.gethostname()

        if sender.endswith("@"):
            sender = sender + 'localhost'

        all_recipients = recipient.split(",") + bcc

        text = "Please view this email in HTML to see the content."

        # Create message wrapper. Ensure MIME encoded message is defined so that
        # e-mail message displays in HTML format on the receiving e-mail client.
        message = MIMEMultipart('alternative')
        message.preamble = 'This is a multi-part message in MIME format.'
        message.add_header('From', sender)
        message.add_header('To', recipient)
        message.add_header('Subject', subject)
        message.add_header('Date', utils.formatdate(localtime=True))
        message.add_header('X-Priority', "3")
        partHtml = MIMEText(body, 'html','utf-8')
        partText = MIMEText(text, 'plain','utf-8')
        # THIS ORDER MATTERS - rfc1341 7.2.3
        message.attach(partText)
        message.attach(partHtml)

        if(csvdata):
            partCsv = MIMEBase("text", "csv")
            partCsv.set_payload(csvdata)
            encoders.encode_base64(partCsv)
            partCsv.add_header('Content-Disposition', 'attachment', filename='sendresults.csv')
            message.attach(partCsv)

        # send the mail
        if not use_ssl:
            smtp = smtplib.SMTP(server)
        else:
            smtp = smtplib.SMTP_SSL(server)
        if use_tls:
            smtp.ehlo()
            smtp.starttls()
        if len(username) > 0 and len(password) >0:
            smtp.login(str(username), str(password))
        smtp.sendmail(sender, all_recipients, message.as_string())
        smtp.quit()

        return time.time()

    except Exception as e:
        logger.error('invocation_id=%s invocation_type="%s" msg="Could not send email" rcpt="%s" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,all_recipients,str(e)))

    return 0

###############################################################################
#
# Function:   generateCsv
#
# Descrition: This function takes an array of events and creates a CSV
#
# Arguments:
#    fields - The fields in the events
#    results - An array of events to make into csv rows
#
###############################################################################

def generateCsv(fields, results):
    buffer = BytesIO()
    textIO = TextIOWrapper(buffer, encoding='utf-8', errors='backslashreplace', newline='', write_through=True,)
    writer = csv.writer(textIO)

    logger.info(fields)
    logger.info(results)

    writer.writerow(fields)
    for result in results:
        row = []
        for f in fields:
            val = result.get(f,"")
            if isinstance(val, list):
                val = ' '.join(map(str,val))
            else:
                row.append(val)

        writer.writerow(row)

    return buffer.getvalue()

######################################################
######################################################
# Helper functions from a canonical splunk script.
#

def unquote(val):
    if val is not None and len(val) > 1 and val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val

def toBool(strVal):
   if strVal == None:
       return False

   lStrVal = strVal.lower()
   if lStrVal == "true" or lStrVal == "t" or lStrVal == "1" or lStrVal == "yes" or lStrVal == "y" :
       return True
   return False

def getarg(argvals, name, defaultVal=None):
    return unquote(argvals.get(name, defaultVal))

######################################################
######################################################
#
# Main
#

logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','sendresults.log'), filemode='a+', level=logger.INFO)

logger.info('invocation_id=%s invocation_type="%s" py_version=%s' % (INVOCATION_ID, INVOCATION_TYPE,str(sys.version_info)))

keywords, argvals  = splunk.Intersplunk.getKeywordsAndOptions()

default_format     = "table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"

em_body_fromArg    = getarg(argvals, "body", "")
em_subject_fromArg = getarg(argvals, "subject", "")
em_sender_fromArg  = getarg(argvals, "sender", "")
em_footer_fromArg  = getarg(argvals, "footer", "")
maxrcpts           = int(getarg(argvals, "maxrcpts", "200"))
result_format      = getarg(argvals, "msgstyle", default_format)
format_columns     = getarg(argvals, "format_columns", "")
showemail          = toBool(getarg(argvals, "showemail", "true"))
showsubj           = toBool(getarg(argvals, "showsubj",  "true"))
showbody           = toBool(getarg(argvals, "showbody",  "true"))
showfooter         = toBool(getarg(argvals, "showfooter",  "true"))
showresults        = toBool(getarg(argvals, "showresults",  "true"))
bccresults         = getarg(argvals, "bcc", "")
fieldorder_arg     = getarg(argvals, "field_order", "")
sendCsv            = toBool(getarg(argvals, "sendcsv",  "false"))
addInfo            = toBool(getarg(argvals, "addinfo",  "false"))
stopOnError        = toBool(getarg(argvals, "stoponerror",  "true"))

fieldorder = []
exclude_cols = []
class_cols = {}
email_result = {}

if format_columns.replace(' ','') != "":
    for col in format_columns.split(","):
        class_cols[col.replace(' ','')] = col.replace(' ','')+'-class'
        exclude_cols.append(col.replace(' ','')+'-class')

if fieldorder_arg.replace(' ','') != "":
    for col in fieldorder_arg.split(","):
        fieldorder.append(col.replace(' ',''))

if bccresults == "":
    bcc = []
else:
    bcc = bccresults.split(",")

results = []
message = '<html>\n'
message += '<head>\n'
message += '<meta charset="UTF-8">\n'
message += '<title>Events Composing Alert</title>\n'
message += '<style>' + result_format + '</style>\n'
message += '</head>\n'
message += '<body>\n'

try:
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

    server_type = getServerType(settings)
    is_cloud = False
    if(server_type == 'cloud'):
        is_cloud = True
    logger.info('invocation_id=%s invocation_type="%s" is_cloud="%s" stopOnError="%s" addInfo="%s"' % (INVOCATION_ID, INVOCATION_TYPE, is_cloud, stopOnError, addInfo))

    getEmailAlertActions(argvals, settings, is_cloud)

    if em_sender_fromArg != "":
        argvals['sender'] = em_sender_fromArg

    recipient_list = defaultdict(list)
    event_list     = defaultdict(list)
    fields         = []
    missing_email  = 0
    header         = ""

    for event in results:
        if ('email_to' in list(event.keys()) and event['email_to'] != ''):
            if event['email_to'] not in list(recipient_list.keys()):

                if em_subject_fromArg != "" :
                    subj = em_subject_fromArg
                elif 'email_subj' in list(event.keys()) :
                    subj = event['email_subj']
                else :
                    subj = "Splunk Alert!"

                if em_body_fromArg != "" :
                    body = em_body_fromArg
                elif 'email_body' in list(event.keys()) :
                    body = event['email_body']
                else :
                    body = "You are receiving this e-mail because a set of sensitive events detected by a splunk search contained your e-mail as the responsible party. Auto-generated results compilation follows:"

                if em_footer_fromArg != "" :
                    footer = em_footer_fromArg
                elif 'email_footer' in list(event.keys()) :
                    footer = event['email_footer']
                else :
                    footer = ""

                recipient_list[event['email_to']] = {'email_subj': subj, 'email_body': body, 'email_footer': footer}

            event_list[event['email_to']].append(event)

            for key in list(event.keys()):
                if key not in fields :
                    if key in exclude_cols:
                        continue
                    if (not key.startswith("__mv_")) and (key != 'email_to' or showemail) and (key != 'email_subj' or showsubj) and (key != 'email_body' or showbody) and (key != 'email_footer' or showfooter):
                        fields.append(key)
        else:
            missing_email += 1

    if(len(fieldorder)):
        fields1 = fields
        fields2 = fieldorder

        s = set(fields1)
        temp1 = [x for x in fields2 if x in s]

        s = set(fields2)
        temp2 = [x for x in fields1 if x not in s]

        fields = temp1+temp2
        logger.info('invocation_id=%s invocation_type="%s" msg="Actual field order" fields=%s' % (INVOCATION_ID,INVOCATION_TYPE,fields))

    logger.info('invocation_id=%s invocation_type="%s" rcpts=%s maxrcpt=%s' % (INVOCATION_ID, INVOCATION_TYPE, len(recipient_list), maxrcpts))

    if maxrcpts < 1 :
        logger.error('invocation_id=%s invocation_type="%s" msg="Field maxrcpts must be greater than 0. Increase your maxrcpts"' % (INVOCATION_ID,INVOCATION_TYPE))
        results = splunk.Intersplunk.generateErrorResults("Error : Field maxrcpts must be greater than 0. Increase your maxrcpts.")
    elif len(recipient_list) > maxrcpts :
        logger.error('invocation_id=%s invocation_type="%s" msg="More emails would be generated than permitted. Increase your maxrcpts or change your search"' % (INVOCATION_ID,INVOCATION_TYPE))
        results = splunk.Intersplunk.generateErrorResults("Error : More than emails would be generated than permitted. Increase your maxrcpts or change your search.")
    elif (stopOnError and missing_email) :
        logger.error('invocation_id=%s invocation_type="%s" msg="All results must contain a field named email_to with the intended recipient"' % (INVOCATION_ID,INVOCATION_TYPE))
        results = splunk.Intersplunk.generateErrorResults("Error : All results must contain a field named email_to with the intended recipient.")
    else :
        header += '<tr>'
        for key in fields :
            header += '<th>' + key + '</th>'
        header += '</tr>\n'

        errorState = False
        for recipient in recipient_list :
            outbound = message
            outbound += '<p id="sendresults_body">\n'
            outbound += recipient_list[recipient].get('email_body')
            outbound += '</p>\n'
            if(showresults):
                outbound += '<table id="sendresults_results">\n'
                outbound += header
                for event in event_list[recipient] :
                    outbound += '<tr>\n'
                    for key in fields :
                        c = ""
                        if class_cols.get(key) != None and event.get(class_cols[key]) != None :
                            c = ' class="' + event[class_cols[key]] + '"'
                        if event.get(key) != None :
                            if isinstance(event[key], str) == True :
                                outbound += '<td'+c+'>' + event[key] + '</td>\n'
                            else:
                                if event[key][0] == "##__SPARKLINE__##" :
                                    outbound += '<td'+c+'>' + ",".join(event[key]) + '</td>\n'
                                else:
                                    outbound += '<td'+c+'>' + "<br />".join(event[key]) + '</td>\n'
                        else:
                            outbound += '<td'+c+'> ______ </td>\n'
                    outbound += '</tr>\n'
                outbound += '</table>\n'
            outbound += '<p id="sendresults_footer">\n'
            outbound += recipient_list[recipient].get('email_footer')
            outbound += '</p>\n'
            outbound += '</body>\n'
            outbound += '</html>\n'

            csvdata = None
            if(sendCsv):
                csvdata = generateCsv(fields,event_list[recipient])

            email_result[recipient] = sendemail(recipient, bcc, recipient_list[recipient].get('email_subj') , outbound, argvals, csvdata)

            if(email_result[recipient]):
                logger.info('invocation_id=%s invocation_type="%s" msg="Email sent" rcpt="%s" subject="%s" events=%d csv=%s' % (INVOCATION_ID,INVOCATION_TYPE,recipient,recipient_list[recipient].get('email_subj'),len(event_list[recipient]),sendCsv))
            else:
                logger.error('invocation_id=%s invocation_type="%s" msg="Email NOT sent" rcpt="%s"' % (INVOCATION_ID,INVOCATION_TYPE,recipient))
                if(stopOnError):
                    errorState = True
                    results = splunk.Intersplunk.generateErrorResults("Error : Error sending email.")
                    break

        if(not errorState):
            if(len(event_list)):
                logger.info('invocation_id=%s invocation_type="%s" msg="All Email alerts successfully sent"' % (INVOCATION_ID, INVOCATION_TYPE))
            else:
                logger.info('invocation_id=%s invocation_type="%s" msg="No Email alerts sent"' % (INVOCATION_ID, INVOCATION_TYPE))

            if(addInfo):
                for event in results:
                    if ('email_to' in list(event.keys()) and event['email_to'] != ''):
                        event["sendresults_sent"] = email_result[event['email_to']] if email_result[event['email_to']] > 0 else -1

except Exception as e:
    logger.error('invocation_id=%s invocation_type="%s" msg="General Error" traceback=%s' % (INVOCATION_ID,INVOCATION_TYPE,str(e)))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(e))

# output results
splunk.Intersplunk.outputResults(results)
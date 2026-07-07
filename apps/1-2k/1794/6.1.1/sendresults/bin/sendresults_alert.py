###############################################################################
###############################################################################
##
##  SENDRESULTS ALERT - a splunk email alert action
##
##  Discovered Intelligence
##  https://discoveredintelligence.ca
##
##  For support contact:
##  support@discoveredintelligence.ca
##
###############################################################################
###############################################################################

import sys
import os
import json
import csv
import gzip
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders, utils
import socket
import string
import random
import time
import json
from collections import defaultdict
import logging as logger
import splunk.entity as entity # pylint: disable=F0401
from splunk.rest import simpleRequest # pylint: disable=F0401
from io import (BytesIO, TextIOWrapper)

## Create a unique identifier for this invocation
NOWTIME         = time.time()
SALT            = random.randint(0, 100000)
INVOCATION_ID   = str(NOWTIME) + ':' + str(SALT)
INVOCATION_TYPE = "action"

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
##-- Helper function to access the server type
##--
def getServerType(settings):

    sessionKey = settings['session_key']
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
        sessionKey = settings['session_key']
        ent = entity.getEntity('admin/alert_actions', 'email', namespace=namespace, owner='nobody', sessionKey=sessionKey)

        argvals['server'] = ent['mailserver']
        argvals['sender'] = ent['from']
        argvals['use_ssl'] = toBool(ent['use_ssl'])
        argvals['use_tls'] = toBool(ent['use_tls'])

        namespace  = settings.get("namespace", None)
        username, password = getCredentials(settings['session_key'], namespace, is_cloud)
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
#    csvdata - CSV data to add.
#
###############################################################################

def sendemail(recipient, bcc, subject, body, argvals, csvdata=None):

    try:
        server = getarg(argvals, "server", "localhost")
        sender = getarg(argvals, "sender", "splunk")
        use_ssl = argvals["use_ssl"]
        use_tls = argvals["use_tls"]
        username = str(getarg(argvals, "username"  , ""))
        password = str(getarg(argvals, "password"  , ""))

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
            smtp.login(username, password)

        smtp.sendmail(sender, all_recipients, message.as_string())
        smtp.quit()
    except Exception as e:
        logger.error('invocation_id=%s invocation_type="%s" msg="Could not send email" rcpt="%s" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,all_recipients,str(e)))
        raise

###############################################################################
#
# Function:   generateCsv
#
# Descrition: This function takes an array of events and creates a CSV
#
# Arguments:
#    fields - The fields in the events
#    header_key - Mapping of array index to field value
#    results - An array of events to make into csv rows
#
###############################################################################

def generateCsv(fields, header_key, results):
    buffer = BytesIO()
    textIO = TextIOWrapper(buffer, encoding='utf-8', errors='backslashreplace', newline='', write_through=True,)
    writer = csv.writer(textIO)

    writer.writerow(fields)
    for result in results:
        row = []
        for f in fields:
            val = result[header_key[f]] or ""
            if isinstance(val, list):
                val = ' '.join(map(str,val))
            else:
                row.append(val)

        writer.writerow(row)

    return buffer.getvalue()

######################################################
######################################################
#
# Main
#

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute" :

        logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','sendresults.log'), filemode='a+', level=logger.INFO)

        logger.info('invocation_id=%s invocation_type="%s" py_version=%s' % (INVOCATION_ID, INVOCATION_TYPE,str(sys.version_info)))

        argvals        = defaultdict(list)
        recipient_list = defaultdict(list)
        event_list     = defaultdict(list)
        fields         = []
        header_key     = {}
        default_format = "table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"

        payload = json.loads(sys.stdin.read())

        server_type = getServerType(payload)
        is_cloud = False
        if(server_type == 'cloud'):
            is_cloud = True
        logger.info('invocation_id=%s invocation_type="%s" is_cloud="%s"' % (INVOCATION_ID, INVOCATION_TYPE, is_cloud))
        getEmailAlertActions(argvals,payload,is_cloud)

        settings = payload.get('configuration')

        em_sender_fromArg  = getarg(settings, "sender", "")
        em_subject_fromArg = getarg(settings, "subject", "")
        em_body_fromArg    = getarg(settings, "body", "")
        em_footer_fromArg  = getarg(settings, "footer", "")
        maxrcpts           = int(getarg(settings, "maxrcpts", "200"))
        result_format      = getarg(settings, "msgstyle", default_format)
        format_columns     = getarg(settings, "format_columns", "")
        showemail          = toBool(getarg(settings, "showemail", "true"))
        showsubj           = toBool(getarg(settings, "showsubj",  "true"))
        showbody           = toBool(getarg(settings, "showbody",  "true"))
        showfooter         = toBool(getarg(settings, "showfooter",  "true"))
        showresults        = toBool(getarg(settings, "showresults",  "true"))
        bccresults         = getarg(settings, "bcc", "")
        fieldorder_arg     = getarg(settings, "field_order", "")
        sendCsv            = toBool(getarg(settings, "sendcsv",  "false"))

        fieldorder = []
        exclude_cols = []
        class_cols = {}

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

        if em_sender_fromArg != "":
            argvals['sender'] = em_sender_fromArg

        if sys.version_info >= (3, 0):
            mode = "rt"
        else:
            mode = "r"

        with gzip.open(payload.get('results_file'),mode) as fin:
            csvreader = csv.reader(fin, delimiter=',')

            headers = next(csvreader, None)
            for index, a in enumerate(headers, start=0):
                header_key[a] = index
                if a not in fields :
                    if a in exclude_cols:
                        continue
                    if (not a.startswith("__mv_")) and (a != 'email_to' or showemail) and (a != 'email_subj' or showsubj) and (a != 'email_body' or showbody) and (a != 'email_footer' or showfooter):
                        fields.append(a)

            if 'email_to' not in header_key:
                logger.error('invocation_id=%s invocation_type="%s" msg="All results must contain a field named email_to with the intended recipient"' % (INVOCATION_ID,INVOCATION_TYPE))
                sys.exit(2)

            if(len(fieldorder)):
                fields1 = fields
                fields2 = fieldorder

                s = set(fields1)
                temp1 = [x for x in fields2 if x in s]

                s = set(fields2)
                temp2 = [x for x in fields1 if x not in s]

                fields = temp1+temp2
                logger.info('invocation_id=%s invocation_type="%s" msg="Actual field order" fields=%s' % (INVOCATION_ID,INVOCATION_TYPE,fields))

            for row in csvreader:
                if row[header_key['email_to']] not in list(recipient_list.keys()):
                    if em_subject_fromArg != "" :
                        subj = em_subject_fromArg
                    elif 'email_subj' in header_key :
                        subj = row[header_key['email_subj']]
                    else :
                        subj = "Splunk Alert!"

                    if em_body_fromArg != "" :
                        body = em_body_fromArg
                    elif 'email_body' in header_key :
                        body = row[header_key['email_body']]
                    else :
                        body = "You are receiving this e-mail because a set of sensitive events detected by a splunk search contained your e-mail as the responsible party. Auto-generated results compilation follows:"

                    if em_footer_fromArg != "" :
                        footer = em_footer_fromArg
                    elif 'email_footer' in header_key :
                        footer = row[header_key['email_footer']]
                    else :
                        footer = ""

                    recipient_list[row[header_key['email_to']]] = {'email_subj': subj, 'email_body': body, 'email_footer': footer}

                for key in header_key:
                    if ("__mv_" + key) in header_key:
                        if row[header_key["__mv_" + key]] != "" :
                            row[header_key[key]] = row[header_key["__mv_" + key]][1:-1].split('$;$')

                event_list[row[header_key['email_to']]].append(row)

        logger.info('invocation_id=%s invocation_type="%s" rcpts=%s maxrcpt=%s' % (INVOCATION_ID, INVOCATION_TYPE, len(recipient_list), maxrcpts))

        if maxrcpts < 1 :
            logger.error('invocation_id=%s invocation_type="%s" msg="Field maxrcpts must be greater than 0. Increase your maxrcpts"' % (INVOCATION_ID,INVOCATION_TYPE))
            sys.exit(2)
        elif len(recipient_list) > maxrcpts :
            logger.error('invocation_id=%s invocation_type="%s" msg="More emails would be generated than permitted. Increase your maxrcpts or change your search"' % (INVOCATION_ID,INVOCATION_TYPE))
            sys.exit(2)
        else :
            header = '<tr>'
            for key in fields :
                header += '<th>' + key + '</th>'
            header += '</tr>\n'

            for recipient in recipient_list :
                outbound = '<html>\n'
                outbound += '<head>\n'
                outbound += '<meta charset="UTF-8">\n'
                outbound += '<title>Events Composing Alert</title>\n'
                outbound += '<style>' + result_format + '</style>\n'
                outbound += '</head>\n'
                outbound += '<body>\n'
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
                            if (class_cols.get(key) != None) and (class_cols[key] in header_key):
                                c = ' class="' + event[header_key[class_cols[key]]] + '"'
                            if event[header_key[key]] != None :
                                if isinstance(event[header_key[key]], str) == True :
                                    outbound += '<td'+c+'>' + event[header_key[key]] + '</td>\n'
                                else:
                                    if event[header_key[key]][0] == "##__SPARKLINE__##" :
                                        outbound += '<td'+c+'>' + ",".join(event[header_key[key]]) + '</td>\n'
                                    else:
                                        outbound += '<td'+c+'>' + "<br />".join(event[header_key[key]]) + '</td>\n'
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
                    csvdata = generateCsv(fields,header_key,event_list[recipient])

                sendemail(recipient, bcc, recipient_list[recipient].get('email_subj') , outbound, argvals, csvdata)
                logger.info('invocation_id=%s invocation_type="%s" msg="Email sent" rcpt="%s" subject="%s" events=%d csv=%s' % (INVOCATION_ID,INVOCATION_TYPE,recipient,recipient_list[recipient].get('email_subj'),len(event_list[recipient]),sendCsv))
            logger.info('invocation_id=%s invocation_type="%s" msg="All Email alerts successfully sent"' % (INVOCATION_ID, INVOCATION_TYPE))
    else:
        logger.error('invocation_id=%s invocation_type="%s" msg="Unsupported execution mode (expected --execute flag)"' % (INVOCATION_ID,INVOCATION_TYPE))
        sys.exit(1)
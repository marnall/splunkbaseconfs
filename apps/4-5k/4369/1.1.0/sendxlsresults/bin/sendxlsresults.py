###############################################################################
###############################################################################
##
##  SENDXLSRESULTS - a splunk email command to send reports as XLS
##
##  Dominique Vocat
##
###############################################################################
###############################################################################

import sys, os, string, shutil, socket
import random
import time
from collections import defaultdict
import splunk.Intersplunk
import splunk.entity as entity
import smtplib, email
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders
import logging as logger

import csv
import re
import xlwt
import copy
from splunk.util import normalizeBoolean

## Create a unique identifier for this invocation
NOWTIME         = time.time()
SALT            = random.randint(0, 100000)
INVOCATION_ID   = str(NOWTIME) + ':' + str(SALT)
INVOCATION_TYPE = "command"

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
#
###############################################################################

def getEmailAlertActions(argvals, settings):
    try:
        namespace  = settings.get("namespace", None)
        sessionKey = settings['sessionKey']
        ent = entity.getEntity('admin/alert_actions', 'email', namespace=namespace, owner='nobody', sessionKey=sessionKey)
        print >> sys.stderr, "entity:"
        print >> sys.stderr, ent

        argvals['server'] = ent['mailserver']
        argvals['sender'] = ent['from']
        argvals['use_ssl'] = ent['use_ssl']
        argvals['use_tls'] = ent['use_tls']
        if 'auth_username' in ent and 'clear_password' in ent:
            argvals['username'] = ent['auth_username']
            argvals['password'] = ent['clear_password']
    except Exception, e:
        logger.error('invocation_id=%s invocation_type="%s" msg="Could not get email alert actions from splunk" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,str(e)))
        raise

###############################################################################
#
# Function:   sendemail
#
# Descrition: This function sends a MIME encoded e-mail message using Splunk SMTP
#              Settings.
#
# Arguments:
#    recipient - maps the the field 'email_to' in the event returned by Search.
#    subject - maps to the field 'subject' in the event returned by Search.
#    body - maps the field 'message' in the event returned by Search.
#    argvals - hash of various arguments needed to configure the SMTP connection etc.
#
###############################################################################

def sendemail(recipient, sender, subject, body, argvals, attachment):


    print >> sys.stderr, "email sender: - recipient: "+recipient+" | subject: "+subject+" | body: "+body+" | attachment:"+attachment
    print >> sys.stderr, argvals
    server    = getarg(argvals, "server", "localhost")
    use_ssl   = toBool(argvals['use_ssl'])
    use_tls   = toBool(argvals['use_tls'])
    username  = getarg(argvals, "username"  , "")
    password  = getarg(argvals, "password"  , "")
    recipient = getarg(argvals, "recipient" , "")

    # make sure the sender is a valid email address
    if (sender.find("@") == -1):
        sender = sender + '@' + socket.gethostname()

    if sender.endswith("@"):
        sender = sender + 'localhost'

    # Create multipart message
    msg = MIMEMultipart()
    msg['Subject'] = subject 
    msg['From'] = sender
    msg['To'] = recipient
    part1 = MIMEText(bodyText, 'plain')
    msg.attach(part1)

    try:
        part2 = MIMEBase('application', "octet-stream")
        part2.set_payload(open(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + attachment, "rb").read())
        Encoders.encode_base64(part2)
        part2.add_header('Content-Disposition', 'attachment; filename="' + attachment + '"')
        msg.attach(part2)
    except Exception, e:
        print >> sys.stderr, "exception while attaching file occured"
        logger.error('invocation_id=%s invocation_type="%s" msg="error attaching file" rcpt="%s" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,recipient,str(e)))
        raise        
    try:
        # send the mail
        if not use_ssl:
            print >> sys.stderr, "plain jane mail"
            smtp = smtplib.SMTP(server)
        else:
            print >> sys.stderr, "use ssl mail"
            smtp = smtplib.SMTP_SSL(server)

        if use_tls:
            print >> sys.stderr, "use TLS"
            smtp.ehlo()
            smtp.starttls()
        if len(username) > 0 and len(password) >0:
            print >> sys.stderr, "user username/password"
            smtp.login(username, password)

        print >> sys.stderr, "go go gadget - send email!"
        print >> sys.stderr, smtp.sendmail(sender, string.split(recipient, ","), msg.as_string())
        smtp.quit()
        return
    except Exception, e:
        print >> sys.stderr, "exception while sending email occured"
        logger.error('invocation_id=%s invocation_type="%s" msg="Could not send email" rcpt="%s" error="%s"' % (INVOCATION_ID,INVOCATION_TYPE,recipient,str(e)))
        raise


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
# converto to workbook to attach later

def csv_to_xls(search_name, output=None):
    if output is None:
        output = sys.stdout
    logger.info("parameters used: outputfile %s" % (output))
    int_re = re.compile(r'^\d+$')
    float_re = re.compile(r'^\d+\.\d+$')
    date_re = re.compile(r'^\d+-\d+-\d+|^\d+\/\d+\/\d+|^\d+\.\d+\.\d+')
    style = xlwt.XFStyle()

    workbook = xlwt.Workbook(encoding="UTF-8") #()
    sheet = workbook.add_sheet(search_name)

    #headers...
    columns = results[0]
    column_num = 0
    for key in results[0].keys():
        if not key.startswith('__'): # skip stuff like __mv
            sheet.write(0, column_num, key)
            column_num += 1
            
    row_num = 0
    for row in results:
        column_num = 0
        for item in row:
            format = 'general'
            cellvalue = ""
            if re.match(date_re, row[item]):
                cellvalue = row[item]
                format = 'M/D/YY'
            elif re.match(float_re, row[item]):
                cellvalue = float(row[item])
                format = '0.00'
            elif re.match(int_re, row[item]):
                cellvalue = float(row[item])
                format = '0'
            else:
                cellvalue = row[item]
                format = ''
            style.num_format_str = format
            sheet.write(row_num +1, column_num, cellvalue, style) #sheet.write(row_num, column_num, unicode(item).encode("utf-8"), style)
            column_num += 1
        row_num += 1
 
    workbook.save(output)
    return True


    
######################################################
######################################################
#
# Main
#

logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','sendxlsresults.log'), filemode='a+', level=logger.INFO)

keywords, argvals  = splunk.Intersplunk.getKeywordsAndOptions()

default_format     = "table {font-family:Arial;font-size:12px;border: 1px solid black;padding:3px}th {background-color:#4F81BD;color:#fff;border-left: solid 1px #e9e9e9} td {border:solid 1px #e9e9e9}"


print >> sys.stderr, "Arguments we received:"
print >> sys.stderr, argvals
bodyText           = getarg(argvals, "body", "")
subject            = getarg(argvals, "subject", "")
sender             = getarg(argvals, "sender", "")
recipient          = getarg(argvals, "recipient", "")
filename           = getarg(argvals, "filename", "")
search_name        = getarg(argvals, "search_name", "one")
smptHost           = getarg(argvals, "server", "localhost")

results = []

try:
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

    getEmailAlertActions(argvals, settings)
    smptHost           = getarg(argvals, "server", "localhost")
    print >> sys.stderr, "smptHost:"
    print >> sys.stderr, smptHost
    
    try:
        csv_to_xls(search_name, os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + filename)
        sendemail(recipient, sender, subject, bodyText, argvals, filename)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        splunk.Intersplunk.generateErrorResults("Error when sending mail: Traceback: '%s'. %s" % (e, stack))
        exit()
    
except:
    import traceback
    stack =  traceback.format_exc()
    logger.error('invocation_id=%s invocation_type="%s" msg="General Error" traceback=%s' % (INVOCATION_ID,INVOCATION_TYPE,str(stack)))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

# output results
splunk.Intersplunk.outputResults(results)

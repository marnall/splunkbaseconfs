import sys,splunk.Intersplunk
import splunk.bundle as bundle
import re

import smtplib
import os
import os.path
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

def send_mail(send_from, send_to, subject, text, files=[], server="localhost"):
    assert type(send_to)==list
    assert type(files)==list
    
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = COMMASPACE.join(send_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach( MIMEText(text) )

    for f in files:
        part = MIMEBase('application', "octet-stream")
        contents = open(f,"rb").read()
        part.set_payload( contents )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)

    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()

try:
    sessionKey = sys.stdin.readline()
    sessionKey = re.findall('<authToken>(.*?)</authToken>',sessionKey)[0]
    #authString:<auth><userId>admin</userId><username>admin</username><authToken>2c1e2bb2741756dda5f2c2c48c6fb40b</authToken></auth> 
    namespace = 'csvutils' # re.findall('.*[\\/](\w+)[\\/]bin',sys.path[0])[0]

    try:
        conf = bundle.getConf('alert_actions', sessionKey=sessionKey) #, namespace=namespace, owner='admin') #extract this from sys.path[0], unless there's a better way

        from_address = conf['email']['from']
        subject = conf['email']['subject']
        mailserver = conf['email']['mailserver']

    except:
        raise Exception("Failed to retrieve alert_actions config. " + str(sys.exc_info()[0]))


    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()

    to_address = argvals.get("to", None)
    if to_address is None:
        raise Exception("Must supply destination address(es) in to=\"x@y.com,y@x.com\".")
    serverURL  = argvals.get("server", mailserver)
    sender     = argvals.get("from", from_address)
    subject    = argvals.get("subject" , subject)

    delete_on_send = argvals.get("delete_on_send" , False)
    if delete_on_send is not False:
        if delete_on_send.strip().lower() in ['true','yes','1']:
            delete_on_send = True

    csvs = argvals.get("csvs", None)
    if csvs is None:
        raise Exception("Must supply csv filename(s) in csvs=\"foo.csv,bar.csv\". These files must exist in $SPLUNK_HOME/var/run/splunk/. This is the location output is saved with the outputcsv command.")

    newResults = []

    files=[]
    for f in csvs.split(","):
        f = os.sep.join( [os.getenv("SPLUNK_HOME") , "var" , "run" , "splunk" , f] )
        if not os.path.exists(f):
            raise Exception("%s doesn't exist! Aborting!" % f)
        newResults.append( dict({'log': "Appending %s to file list." % f}) )
        files.append(f)

    send_mail( sender, to_address.split(","), subject, ( "Splunk CSV results.\n%d file(s) attached.\n\n" % len(files) ), files, serverURL )
    newResults.append( dict({'log': "Mail sent with %d file(s)." % len(files)}) )
    
    if delete_on_send:
        for f in files:
            os.unlink(f)
            newResults.append( dict({'log': "Removing file %s." % f}) )

except:
    import traceback
    stack =  traceback.format_exc()
    newResults = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( newResults )


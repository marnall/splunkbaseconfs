#!/opt/splunk/bin/python
# Copyright 2014 (c) Helvetia Versicherungen, Switzerland
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>
# sendfile tool for Splunk
# note: limited to files in the $SPLUNK_HOME/var/run/splunk/ . Uses code fro someone else, see included copyright block.
# version 0.2.1
# changes in 0.1.1, i previously failed to properly set the mail body text as a part. No html part implemented yet.
# changes in 0.2, prettify
# changes in 0.2.1, python 2,3 cross compatibility

# send a text email from the command line using python
#
# created 6/25/09 by Hank McShane
# version 1.0
#
# The code at the following URL was modified to create this script:
# http://www.cs.cmu.edu/~benhdj/Mac/unix.html#smtpScript
#
# NOTE: if smtp username is "" then code will not use the smtp authentication method
#
# input parameters
#   sys.argv[1] is the sender email address
#   sys.argv[2] is the reciever email address,
#       this can be a comma separated string for multiple recievers
#   sys.argv[3] is the subject text
#   sys.argv[4] is the body text
#   sys.argv[5] is the smtp host
#   sys.argv[6] is the smtp username
#   sys.argv[7] is the smtp password
#   sys.argv[8] is the smtp port
#
from __future__ import print_function
__author__ = 'VTD'

# import Python Modules
import sys, datetime, getopt, os, splunk.Intersplunk, csv, re, time, calendar, xlwt, re, argparse, gzip, csv, splunk.mining.dcutils
from datetime import datetime
from six.moves.configparser import SafeConfigParser
from optparse import OptionParser

logger = splunk.mining.dcutils.getLogger()

import smtplib, email
from email.MIMEMultipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders

# check to make sure the number of arguments is correct
if len(sys.argv) < 4:
    #print 'Usage: pythonEmail.py <sender> <receiver> <subject> <bodyText> <smptHost> <username> <password> <port>'
    splunk.Intersplunk.generateErrorResults("Usage: pythonEmail.py <sender> <receiver> <subject> <bodyText> <smptHost> <username> <password> <port>")  
    #sys.exit(1)
    exit()

# get the argv variables
sender = sys.argv[1]
receiver = sys.argv[2]
subj = sys.argv[3]
bodyText = sys.argv[4]
attachment = sys.argv[5]
smtpHost = sys.argv[6]
#username = sys.argv[7] # use "" if no SMTP authentication is required
#passwd = sys.argv[8] # ignored if no SMTP authentication is required
#port = sys.argv[9] # ignored if no SMTP authentication is required
username = ""
  
# create a list from the receiver in case we have a comma separated string of multiple receivers
rList = []
rList = receiver.split(',');

# setup the message header
timegmt = time.gmtime(time.time( ))
fmt = '%a, %d %b %Y %H:%M:%S GMT'
datestr = time.strftime(fmt, timegmt)
#msg = 'From: %s\nTo: %s\nDate: %s\nSubject: %s\n%s' % (sender, receiver, datestr, subj, bodyText)
msg = MIMEMultipart()
msg['Subject'] = subj 
msg['From'] = sender
msg['To'] = receiver

part1 = MIMEText(bodyText, 'plain')
msg.attach(part1)

part2 = MIMEBase('application', "octet-stream")
part2.set_payload(open(os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/" + attachment, "rb").read())
Encoders.encode_base64(part2)

part2.add_header('Content-Disposition', 'attachment; filename="' + attachment + '"')

msg.attach(part2)
       
# determine if a passworded smpt host is being used and connect as necessary
if username == "":
    server = smtplib.SMTP(smtpHost) # smtp server is not password protected
else:
    server = smtplib.SMTP(smtpHost, port)
    server.login(username, passwd)

failed = server.sendmail(sender, rList, msg.as_string())
server.quit() 

# return the status
if failed:
    #print 'pythonEmail.py: Failed:', failed
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
else:
    print ('pythonEmail.py: Finished with no errors.')


# Copyright (C) 2005-2011 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import sys, string
from socket import *

# Hardcode the number of the finger port here.                                 
# It's not likely to change soon...                                          
#                                                                              
FINGER_PORT = 79
# uses ftp_address field to anonymous ftp to site and returns status

# Function to do one remote finger invocation.
# Taken from http://svn.python.org/projects/python/trunk/Demo/sockets/finger.py
#
def finger(host, args):
    s = socket(AF_INET, SOCK_STREAM)
    s.settimeout(3)
    s.connect((host, FINGER_PORT))
    s.send(args + '\n')
    buf=""
    while 1:
        tempbuf = s.recv(1024)
        if not tempbuf: break
        buf = buf + tempbuf
    return buf

addressfield="finger_address"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |fingerstatus finger_address as <local-field>")
    sys.exit()
elif len(sys.argv) == 4:
    addressfield=sys.argv[3]


results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if addressfield in r:
                fingerresult=""
                r["fingerstatus"] = "none"

                try:
                    # connect to host default port
                    finger_address=r[addressfield]
                    if '@' in finger_address:
                        at = string.index(finger_address, '@')
                        host = finger_address[at+1:]
                        user = finger_address[:at]
                    else:
                        host = ''
                        user=finger_address
                    fingerresult=finger(host, user)
                    if fingerresult!='':
                        r["fingerstatus"] = fingerresult
                    else:
                        r["fingerstatus"] = "none"
                except:
                        r["fingerstatus"] = "none"


except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

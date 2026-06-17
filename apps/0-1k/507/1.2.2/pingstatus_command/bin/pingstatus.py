# Copyright (C) 2005-2011 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import ping
import socket


urlfield="url"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |pingstatus url as <local-field> (or have url field name in data)")
    sys.exit()
elif len(sys.argv) == 4:
    urlfield=sys.argv[3]

results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if urlfield in r:
                try:
                    delay = ping.do_one(r[urlfield], timeout=2)
                    r["pingdelay"] = delay
                except socket.error as e:
                    r["pingdelay"] = 10000000
except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import http.client

urlfield="url"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |httpstatus url as <local-field> (or have url field name in data)")
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
                    conn = http.client.HTTPSConnection(r[urlfield], timeout=5)
                    conn.request("HEAD","")
                    res = conn.getresponse()
                    r["httpstatus"] = res.status
                    conn.close()
                except:
                    r["httpstatus"] = "0"
                    if (conn != None):
                        conn.close()
except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

# Copyright (C) 2005-2017 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import http.client

urlfield="url"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |httpget url as <local-field> (or have url field name in data)")
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
                    conn.request("GET", "/")
                    r1 = conn.getresponse()
                    data = r1.read(1024)
                    r["httpget"] = data
                    conn.close()
                except:
                    r["httpstatus"] = ""
                    if (conn != None):
                        conn.close()
except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

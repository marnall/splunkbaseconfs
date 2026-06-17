# Copyright (C) 2005-2014 Splunk Inc.  All Rights Reserved.  Version 6.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
import getpass
import telnetlib

# uses telnet_address field to telent to site and returns status

addressfield="telnet_address"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |telnetstatus telnet_address as <local-field>")
    sys.exit()
elif len(sys.argv) == 4:
    addressfield=sys.argv[3]

results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if addressfield in r:
                connected=False
                loginfound=False
                r["telnetstatus"]="None"
                tn=None
                try:
                    # connect to host default port
                    tn = telnetlib.Telnet(host=r[addressfield], timeout=3)
                    connected=True
                    tn.read_until(b"login: ", timeout=3)
                    loginfound=True
                    tn.close()
                    r["telnetstatus"] = "LoginFound"
                except:
                    if r[addressfield] != "":
                        if (connected==True and loginfound==False):
                            r["telnetstatus"]="LoginNotFound"
                            if tn:
                                tn.close()
                            elif (connected==False):
                                if tn:
                                    tn.close()

except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

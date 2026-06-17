# Copyright (C) 2005-2014 Splunk Inc.  All Rights Reserved.  Version 6.x
# Author: Nimish Doshi
import sys,splunk.Intersplunk
import string
from ftplib import FTP

# uses ftp_address field to anonymous ftp to site and returns status

addressfield="ftp_address"

if len(sys.argv)>1 and len(sys.argv) != 4:
    print ("Usage |fptstatus ftp_address as <local-field>")
    sys.exit()
elif len(sys.argv) == 4:
    addressfield=sys.argv[3]

results = []

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if "_raw" in r:
            if addressfield in r:
                ftp=None
                try:
                    # connect to host default port
                    ftp = FTP(host=r[addressfield], timeout=3)
                    ftp.login()
                    ftp.quit()
                    r["ftpstatus"] = "connected"
                except:
                    if r[addressfield] != "":
                        r["ftpstatus"] = "not_connected"


except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

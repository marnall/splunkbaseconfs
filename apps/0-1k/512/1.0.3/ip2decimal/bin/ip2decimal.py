# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.0
# Author: Nimish Doshi

""" 
Converts an IP address to decimal format
"""

import sys,splunk.Intersplunk
import re

# def by Tony Veijalainen @  http://www.daniweb.com/code/snippet282977.html
def ipnumber(ip):
    ip=ip.rstrip().split('.')
    ipn=0
    while ip:
              ipn=(ipn<<8)+int(ip.pop(0))
    return ipn




ipre = re.compile("\d+\.\d+\.\d+\.\d+")

results = []


try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()


    
    ipDecimalCache = {}

    for r in results:
        if "_raw" in r:
            raw = r["_raw"]
            ips = ipre.findall(raw)
            i = 0
            for ip in ips:
                postfix = ""
                if( i > 0 ):
                    postfix = str(i)
                    
                r["ip" + postfix ] = ip

                if( ip in ipDecimalCache ):
                    num = ipDecimalCache[ip]
                else:
                    num = ipnumber(ip)
                    ipDecimalCache[ip] = num
                
                r["ipdecimal" + postfix ] = num
                
                i = i + 1
                
except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

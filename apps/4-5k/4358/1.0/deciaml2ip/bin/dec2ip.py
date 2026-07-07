# Copyright (C) 2017-2018 Splunk Inc.  All Rights Reserved.  Version 1.0
# Author: Mohammadreza Sarai 

""" 
Converts an Decimal format to IP address 
"""
import sys,splunk.Intersplunk
import string

if len(sys.argv) == 3:
    input_field=sys.argv[1]
    output_field=sys.argv[2]
else:
    sys.exit()

results = []

#dec2ip = lambda n: '.'.join([str(n >> (i << 3) & 0xFF) for i in range(0, 4)[::-1]])

    ip2int = lambda ip: reduce(lambda a, b: (a << 8) + b, map(int, ip.split('.')), 0)
#int2ip = lambda n: '.'.join([str(n >> (i << 3) & 0xFF) for i in range(0, 4)[::-1]])

try:

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for r in results:
        if input_field in r:
            try:
                r[output_field] = ip2int(int(r[input_field]))
            except:
                r[output_field] = "error"

except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

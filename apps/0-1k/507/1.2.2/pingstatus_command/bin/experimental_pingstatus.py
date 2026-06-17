# Copyright (C) 2005-2011 Splunk Inc.  All Rights Reserved.  Version 4.x
# Author: Nimish Doshi
# Modified by: Arkady Zilberberg, 2015-03-31
# Change history:
#   Added an optional count of pings (see Usage: comment below)
#   Adds fields:
#        pingdelay (just as the original, though now averaged between successful pings)
#        pingsuccess - the count of successful pings
#        pingfail - the count of failed pings
#        pingdelay1 through pingdelay<n> - actual pingdelays for each ping
import sys,splunk.Intersplunk
import string
import ping
import socket


urlfield="url"
count = 1

# Usage:
# pingstatus (ping once, generate pingdelay)
# pingstatus count (ping count of times, generate pingdelay - average, pingloss - tally the losses)
# pingstatus url as local-field (ping once, getting url from local-field)
# pingstatus url as local-field count (ping count of times, generate pingdelay - average, pingloss, get url from local-field)
if len(sys.argv) == 1:
    pass
elif len(sys.argv) == 2:
    count = int(sys.argv[1])
elif len(sys.argv) == 4:
    urlfield=sys.argv[3]
elif len(sys.argv) == 5:
    urlfield = sys.argv[3]
    count = int(sys.argv[4])
else:
    print ("Usage | pingstatus [url as <local-field>] [count] (or have field named 'url' in data)")
    sys.exit()

results = []

try:

     results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

     for r in results:
         if urlfield in r:
             total_delay = 0
             pingsuccess = 0
             pingfail = 0
             for i in range(1, count + 1):
                 try:
                     delay = ping.do_one(r[urlfield], timeout=2)
                     total_delay += delay
                     pingsuccess += 1
                     pingdelay = "pingdelay" + str(i)
                     r[pingdelay] = delay
                     del delay
                 except NameError:
                     pingfail += 1
                 except TypeError:
                     pingfail += 1
                 except socket.error as e:
                     pingfail += 1
                 r["pingdelay"] = 10000000 if pingsuccess == 0 else total_delay / pingsuccess
                 r["pingsuccess"] = pingsuccess
                 r["pingfail"] = pingfail
except:
     import traceback
     stack =  traceback.format_exc()
     results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )

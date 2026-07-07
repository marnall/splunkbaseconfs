#!/usr/bin/python2

import sys
import re
import time
from socket import inet_aton
import math
import csv
import splunk.Intersplunk


def get_net_size(netmask):
    binary_str = ''
    for octet in netmask:
        binary_str += bin(int(octet))[2:].zfill(8)
    return str(len(binary_str.rstrip('0')))

def validation_ipaddress(ip):
        parts=ip.split(".")
        if len(parts)<4 or len(parts)>4:
            return False
        else:
            while len(parts)== 4:
                if ((not parts[0]) or (not parts[1]) or  (not parts[2]) or (not parts[3] )):
                  return False
                a=int(parts[0])
                b=int(parts[1])
                c=int(parts[2])
                d=int(parts[3])
                if a<= 0 or a > 255 :
                    return False
                elif b>255 or b<0:
                    return False
                elif c>255 or c<0:
                    return False
                elif d>255 or c<0:
                    return False
                else:
                    return True


# A basic shell for any custom streaming command. Just pass the events to it
def getipcidr(ipaddress,ipmask, results):
   try:
      for result in results:
        ipaddress_field_exists = 0
        ipmask_field_exists = 0
        # If field exists in event
        if ipaddress in result:
           # Get the field's actual value
           ipaddress_field_exists = 1
           ipaddress_value = result[ipaddress]
           if (validation_ipaddress(ipaddress_value) == True):
             ipaddress_field_exists = 1
           else:
             ipaddress_field_exists = 0
           ipaddr = ipaddress_value.split('.')
        if ipmask in result:
           ipmask_field_exists = 1
           ipmask_value = result[ipmask]
           if (validation_ipaddress(ipmask_value) == True):
             ipmask_field_exists = 1
           else:
             ipmask_field_exists = 0
           netmask = ipmask_value.split('.')
        # Create the new field we'll place into the events
        newfield = "ipcidr"
           

        if (ipaddress_field_exists == 1) and (ipmask_field_exists == 1) :
           # calculate network start
           net_start = [str(int(ipaddr[x]) & int(netmask[x]))
              for x in range(0,4)]
           # Finally, run the math on the field's value and place it into the newfield we just created
           result[newfield] =  '.'.join(net_start) + '/' + get_net_size(netmask)
        else:
           result[newfield] = "N/A"

      # Let the modified events flow back into the search results
      splunk.Intersplunk.outputResults(results)

   except:
	import traceback
	stack =  traceback.format_exc()


 #####Start######
 # Get the events from splunk
results, unused1,unused2  = splunk.Intersplunk.getOrganizedResults()
 # Send the events to be worked on
results = getipcidr(sys.argv[1], sys.argv[2], results)


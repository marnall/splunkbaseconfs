#!/usr/bin/env python
# python cidr_iprange.py 200.100.33.65/26
# Reference : https://gist.github.com/nboubakr/4344773

import sys
import re
import time
from socket import inet_aton
import math
import csv
import splunk.Intersplunk

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




def getiprange(cidrfield, results):
  try:
    for result in results:
      # Get address string and CIDR string from command line
      if cidrfield in result:
        cidr_value = result[cidrfield]
        cidr_parts = cidr_value.split('/')

        # Split address into octets and turn CIDR into int
        length = len(cidr_parts)
        addrString=cidr_parts[0]
        addr = addrString.split('.')
        #exit (len(addr))
        if (length == 2 ):
          cidr = int(cidr_parts[1])
        else:
          cidr = 32
       
        if ( (cidr < 0) or (cidr > 32) or (validation_ipaddress(addrString) == False) ):
          result['firstIP'] = "NA"
          result['lastIP']  = "NA"
          result['netMask'] = "NA"
        else:
          # Initialize the netmask and calculate based on CIDR mask
          mask = [0, 0, 0, 0]
          for i in range(cidr):
            mask[i/8] = mask[i/8] + (1 << (7 - i % 8))
    
          # Initialize net and binary and netmask with addr to get network
          net = []
          for i in range(4):
            net.append(int(addr[i]) & mask[i])
    
          # Duplicate net into broad array, gather host bits, and generate broadcast
          broad = list(net)
          brange = 32 - cidr
          for i in range(brange):
            broad[3 - i/8] = broad[3 - i/8] + (1 << (i % 8))
    
          result["firstIP"] = ".".join(map(str, net))
          result["lastIP"]  = ".".join(map(str, broad))
          result["netMask"] = ".".join(map(str, mask))
    
    # Let the modified events flow back into the search results
    splunk.Intersplunk.outputResults(results)
  except:
    import traceback
    stack =  traceback.format_exc()

#####Start######
# Get the events from splunk
results, unused3,unused4  = splunk.Intersplunk.getOrganizedResults()
# Send the events to be worked on
results = getiprange(sys.argv[1], results)



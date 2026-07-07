#!/usr/bin/env python

#import numpy 
import csv
import sys
import re


# udp/port:5353
# tcp/port:1659
# proto:2/port:0
# rip


def process_protocol(raw_protocol):
    try:
        protocol = raw_protocol.replace("port:","")
        matchObj = re.match( r'proto:(\d+)/port:(\d+)', raw_protocol, re.M|re.I)
        if matchObj:
           protocol = "ip/"+matchObj.group(1)        
        return protocol
    except:
        return raw_protocol

def main():
    if len(sys.argv) != 3:
        print "Usage: python fg_protocol_proc.py [raw_protocol] [protocol]"
        print sys.argv[1]
        print len(sys.argv)
        sys.exit(1)

    raw_protocolfield = sys.argv[1]
    protocolfield = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        if result[raw_protocolfield]:
            result[protocolfield] = process_protocol(result[raw_protocolfield])			
            if result[protocolfield]:
                w.writerow(result)
        else:
            result[protocolfield] = "blah"
            w.writerow(result)

main()

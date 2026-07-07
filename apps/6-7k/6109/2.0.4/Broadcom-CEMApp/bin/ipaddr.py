#!/usr/bin/env python

from __future__ import print_function
import csv
import sys
import socket

""" An adapter that takes CSV as input, performs a lookup to resolve hex ip address 
	to standard IPv4 address, then returns the CSV results.
	
	Note that this script does not convert an IPv4 address to hex ip address, it just 
	returns the same value i.e., Ipv4 address itself. 

    This is intended as an example of creating external lookups in general.
"""
      
#Given a hex ip address, return IPv4 decimal
def convert_hex_ip_to_decimal(hexip):
    try:
        decip = str(int(hexip[0:2], 16)) + "." + str(int(hexip[2:4], 16)) + "." + str(int(hexip[4:6], 16)) + "." + str(int(hexip[6:8], 16))
        return decip
    except:
        return ''

def main():
    if len(sys.argv) != 3:
        print ("Usage: python ipaddr.py [decimal ip] [hex ip]")
        sys.exit(1)

    decimalip = sys.argv[1]
    hexip = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        # Perform the lookup or reverse lookup if necessary
        if result[decimalip] and result[hexip]:
            # both fields were provided, just pass it along
            w.writerow(result)

        elif result[decimalip]:
            # only decimal ip was provided, add hex ip same as decimal ip
            result[hexip] = decimalip
            w.writerow(result)

        elif result[hexip]:
            # only hex ip was provided, add decimal ip
            result[decimalip] = convert_hex_ip_to_decimal(result[hexip])
            if result[decimalip]:
                w.writerow(result)
main()

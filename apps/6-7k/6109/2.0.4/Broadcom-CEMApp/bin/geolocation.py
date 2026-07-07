#!/usr/bin/env python

from __future__ import print_function
import csv
import sys
import socket
import json
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error

""" An adapter that takes CSV as input, performs a lookup resolve an hex ip 
	address to it's country name, then returns the CSV results 

    This is intended as an example of creating external lookups in general.

    Note that this script does not do a reverse lookup. 
"""

# Given an IPv4 address, return the geolocation
def rlookup(ip):
    try:
        if ip:
           ip = ip 
        else:
           ip = "127.0.0.1" # If ip address is not provided, then return loopback ip address
        ipstats = six.moves.urllib.request.urlopen('http://freegeoip.net/json/' + ip).read()
        return json.loads(ipstats)['country_name'].strip()
    except:
        return ''
        
#Given a hex ip address, return IPv4 decimal
def convert_hex_ip_to_decimal(hexip):
    try:
        decip = str(int(hexip[0:2], 16)) + "." + str(int(hexip[2:4], 16)) + "." + str(int(hexip[4:6], 16)) + "." + str(int(hexip[6:8], 16))
        return decip
    except:
        return ''

def main():
    if len(sys.argv) != 3:
        print ("Usage: python geolocation.py [country name] [hex ip field]")
        sys.exit(1)

    countryname = sys.argv[1]
    hexipfield = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        # Perform the lookup or reverse lookup if necessary
        if result[countryname] and result[hexipfield]:
            # both fields were provided, just pass it along
            w.writerow(result)

        elif result[hexipfield]:
            # only ip was provided, add country name
            result[countryname] = rlookup(convert_hex_ip_to_decimal(result[hexipfield]))
            if result[countryname]:
                w.writerow(result)
main()

#!/usr/bin/env python

import csv
import sys
import socket

""" An adapter that takes CSV as input, performs a lookup to the operating
    system hostname resolution facilities, then returns the CSV results 

    This is intended as an example of creating external lookups in general.

    Note that the script offers mapping both ways, from host to IP and from IP
    to host.  
    
    Bidrectional mapping is always required when using an external lookup as an
    'automatic' lookup: one configured to be used without explicit reference in
    a search.

    In the other use mode, eg in a search string as "|lookup lookupname", it is
    sufficient to provide only the mappings that will be used.

    WARNING: DNS is not unambiguously reversible, so this script will produce
             unusual results when used for values that do not reverse-resolve to
             their original values in your environment.

             For example, if your events have host=foo, and you search for
             ip=1.2.3.4, the generated search expression may be
             host=foo.yourcompany.com, which will not match.
"""

# Given an ip, return the host
def inrlookup(ip):
    try:
        hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)		
        return hostname
    except:
        return ip

def main():
    if len(sys.argv) != 3:
        print "Usage: python fg_lookup.py [host field] [ip field]"
        sys.exit(1)

    hostfield = sys.argv[1]
    ipfield = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        if result[ipfield]:
            # only ip was provided, add host
            result[hostfield] = inrlookup(result[ipfield])			
            if result[hostfield]:
                w.writerow(result)

main()

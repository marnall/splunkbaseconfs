# Score Lookup Script

"""

Version: 1.1

Descripton:
    This script creates an online lookup in the Project Honeypot database.
    The lookup is done via a DNS Request and gives a score value of the IP back. 
    If the IP is not found in the database the threadscore will be 0

Prerequierements:
    Register at http://www.projecthoneypot.org and request an http:BL Key.
    
Configuration:
    Copy the http:BL Key into the VAR key.

Input:
    script %IP%
    
Output:
    %IP% %SCORE%
    
Feedback: matthias@splunk.com
    
"""
#

### Library Import

import sys #Sys for argv command
import socket #Socket for Gethosbyname command
import csv #for splunk batch input/output
from time import * 

###### PUT YOUR HTTPBL KEY HERE ######
# Sample: key ='123456abcde'

key = 'putyourkeyhere'

###### PUT YOUR HTTPBL KEY HERE ######

##### Enabling Debuging for the Script ####
debug = 0
if debug==1:
    f = open('score_lookup_log.txt', 'a+')


### Static Input ####
#ip_address = '74.125.129.94'

DNSBL_SUFFIX = 'dnsbl.httpbl.org'

def scorelookup(clientip):
#print
#print "---------------------------------------"
#print "IP Scoring"
#print "----- Data Input to the Script ------"
#print "IP-Address to Query:     ", ip_address
#print "http:BL Access Key:      ", key
#print "DNS Server to query:     ", DNSBL_SUFFIX
#print "----- Data Input to the Script ------"
#print
    ip_address = clientip
    if debug==1:
        f.write("\n Lookup: ")
        f.write(ip_address)

    # Revert IP address
    reverseip = '.'.join(ip_address.split('.')[::-1]) # Split IP Address into . then reverse it and rebuild it
    #print "reverseip:               ", reverseip

    # Create the DNS query
    dns_query = '%s.%s.%s' % (key, reverseip, DNSBL_SUFFIX)
    #print "DNS Query:               ", dns_query
    #dns_response = socket.gethostbyname(dns_query)

    try: 
        dns_response = socket.gethostbyname(dns_query)
    except socket.gaierror: 
        dns_response = "127.0.0.1"
    #print "DNS Response:            ", dns_response
    # Decode Query

    visitor_type, threat_score, days_since_last_activity, response_code = \
                [int(octet) for octet in dns_response.split('.')[::-1]]

    
    #print "Visitor Type:           ", visitor_type
    #print "Threadscore:             ", threat_score
    #print "Days since last Activity:", days_since_last_activity
    #print "Response Code:           ", response_code
    
    # in case visitor type = 0 it's a search engine. threatscore is used in this case as reference which search engine it belongs to.
    if visitor_type==0:
       threat_score=0
    if debug==1:
        f.write(strftime("\n%Y-%m-%d %H:%M:%S"))
        f.write(" source_ip=%s,hist_threatscore=%s" % (ip_address,threat_score))
        f.write(" , hist_visitor_type=%s" % (visitor_type))
    #print "OUTPUT"
    return (ip_address,threat_score,days_since_last_activity,visitor_type)

def main():
    #print 'starte main'
    
    if len(sys.argv) != 3:
        print "Usage: python [ip field] [threatscore]"
        sys.exit(0)
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    clientip = sys.argv[1]
    threatscore = sys.argv[2]
        
    header = []
    first = True

    for line in r:
        if first:
            header = line
            if clientip not in header:
                print "IP field must exist in CSV data"
                sys.exit(0)
            csv.writer(sys.stdout).writerow(header)
            w = csv.DictWriter(sys.stdout, header)
            first = False
            continue

        # Read the result
        result = {}
        i = 0
        while i < len(header):
            if i < len(line):
                result[header[i]] = line[i]
            else:
                result[header[i]] = ''
            i += 1

        # Perform the lookup
        if len(result[clientip]):
            ip_address, threat_score, days_since_last_activity, visitor_type = scorelookup(result[clientip])
            out = "%s,%s,%s,%s" % (ip_address, threat_score, days_since_last_activity, visitor_type)
            print out

main()

if debug==1:
    f.close()

# Testvalue: 14.139.155.194 Result: score 35
# Testvalue: 188.192.20.179 Result: score 0
# Testvalue: 66.249.66.1 Result: score 0 - response from honeypot 5 but last octet is zero so the third octet is the type of search engine and not malicous
# Score Lookup Script
import csv
import sys
import socket
#import commands

###### PUT YOUR HTTPBL KEY HERE ######
key = ''

DNSBL_SUFFIX = 'dnsbl.httpbl.org'

def scorelookup(ipaddr):
	
	if len(key):
		ip_address = ipaddr

		reverseip = '.'.join(ip_address.split('.')[::-1])
		
		dns_query = '%s.%s.%s' % (key, reverseip, DNSBL_SUFFIX)
		
		dns_response = socket.gethostbyname(dns_query)

		try: 
			dns_response = socket.gethostbyname(dns_query)
		except socket.gaierror: 
			dns_response = "127.0.0.1"

		visitor_type, threat_score, days_since_last_activity, response_code = \
					[int(octet) for octet in dns_response.split('.')[::-1]]
		results=[visitor_type, threat_score, days_since_last_activity, response_code];
	else:
		results=[0,0,0,0]
		
	return results


def main(argv):
	
	if len(sys.argv) != 5:
		sys.exit(0)

	dst = sys.argv[1]
	tscore = sys.argv[2]
	vtype = sys.argv[3]
	rcode = sys.argv[4]
	r = csv.reader(sys.stdin)
	w = None
	header = []
	first = True

	for line in r:
		if first:
			header = line
			if dst not in header or tscore not in header or vtype not in header or rcode not in header:				
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
	
		
		w.writerow(result)	

		try:	
			rs =scorelookup(result[dst])
			result[tscore] = rs[1]	
			result[vtype] = rs[0]	
			result[rcode] = rs[3]			
			w.writerow(result)
			
		except socket.gaierror:
			result[tscore] = '0'
			result[vtype] = ' '
			result[rcode] = ' '
			w.writerow(result)
		
main(sys.argv[1:])

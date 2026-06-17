#!/opt/splunk/bin/python
############################################################
#
# Look up MD5/SHA-1 hashes against the Malware Hash Registry 
#
# This version does not support streaming of results, but
# reduces load on the Team Cymru site by sending a single
# bulk query.
#
############################################################
import sys
import splunk.Intersplunk as si
from socket import *


WHOIS_SERVER = 'hash.cymru.com'
WHOIS_PORT   = 43



def whois_query(q, server=WHOIS_SERVER):
	###  Bulk mode; hash.cymru.com [2009-11-12 19:39:50 +0000]
	###  SHA1|MD5 TIME(unix_t) DETECTION_PERCENT
	#
	# 7697561ccbbdd1661c25c86762117613 1258054790 NO_DATA
	# cbed16069043a0bf3c92fff9a99cccdc 1231802137 69
	# ...
	# e6dc4f4d5061299bc5e76f5cd8d16610 1258054790 NO_DATA
	#
	result = ''
	s = socket(AF_INET, SOCK_STREAM)
	s.connect((WHOIS_SERVER, WHOIS_PORT))

	query = q.strip() + '\r\n'
	s.send(query)

	block = s.recv(1024)
	while len(block):
		result += block
		block = s.recv(1024)
	return result



# Figure out which field name(s) contain the hashes
if len(sys.argv) > 1:
	fields = sys.argv[1:]
else:
	fields = ['md5_new', 'sha1sum_new']



# Start processing results
cache = {}
try:
	results,dummyresults,settings = si.getOrganizedResults()

	# First pass extracts all hashes from the result set
	hashes = {}
	for r in results:
		for field_name in fields:
			if field_name in r:
				hash = r[field_name].lower()
				hashes[hash] = 1


	# Perform a bulk whois query for the hashes and fill the cache
	# Skip if we didn't find any hashes.
	if len(hashes) > 0:
		query  = 'begin\r\n'
		query += '\r\n'.join(hashes)
		query += '\r\nend\r\n'

		answer = whois_query(query)

		for line in answer.split('\n'):
			parts = line.split()
			if len(parts) == 3:
				cache[parts[0]] = parts
			

	# Second pass adds the results into the dataset
	for r in results:
		malware_score = 0
		for field_name in fields:
			if field_name in r:
				hash = r[field_name].lower()
				if hash in hashes:
					answer = cache[hash]
					r[field_name + '_detection_last'] = answer[1]
					r[field_name + '_detection_percent'] = answer[2]

					# Track the highest detection percentage for this result
					try:
						tmpscore = int(answer[1])
					except:
						tmpscore = 0

					if tmpscore > malware_score:
						r['malware_score'] = tmpscore

		if malware_score > 0:
			r['is_malware'] = True
		else:
			r['is_malware'] = False



except:
	import traceback
	stack = traceback.format_exc()
	results = si.generateErrorResults("Error : Traceback: " + str(stack))


si.outputResults(results)

import os
import re
import sys
import csv
import codecs
import logging, logging.handlers

from liburlparser import URLParser


########
# MAIN #
########

header  = ['url', 'list', 
	'url_hostname', 'url_netloc', 'url_params', 'url_subdomain', 'url_scheme', 
	'url_path', 'url_domain_without_tld', 'url_domain', 'url_subdomain_depth', 
	'url_fragment', 'url_subdomain_parts', 'url_tld', 'url_port', 'url_query',
	'url_username', 'url_password'
]

csv_in  = csv.DictReader(sys.stdin) # automatically use the first line as header
csv_out = csv.DictWriter(sys.stdout, header)
csv_out.writerow(dict(zip(header,header))) # write header

_init  = False

urlparser = URLParser()

for row in csv_in:
	if not _init :
		if not 'list' in row :
			raise ValueError("parameter list is missing. please specify the TLD list to use.")

		try:
			urlparser.loadTLDList( row['list'] )
			urlparser.setParsingMode( 'extended' )
			_init = True
		except Exception, e:
			msg = "Failed to load TLD list with error: %s" % str(e)
			urlparser.logger.error(msg)
			raise ValueError(msg)

	try:
		res = urlparser.parse( row['url'] )
		row.update(res.to_json())
	except Exception, e:
		raise ValueError("urlparser_lookup: caught exception: %s" % str(e))

	# return row to Splunk
	csv_out.writerow(row)


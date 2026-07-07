#!/usr/bin/python
#-*- Mode: python -*-

'''
Code kindly lifted from the API examples directory
hacked by: Jeremy Guarini
this script should get data for a given device
'''

from __future__ import unicode_literals

import os
import sys
import traceback
import time
import optparse
import datetime
import csv
import base64

from dateutil.relativedelta import relativedelta

# these are the modules that don't come with the splunk python install
# thus an external python environment is needed to install and use the modules
import pyamf
from pyhop import pyhop

debug = 0


def get_connection(username,password,hostname):
	if debug: print "inside get_connection def"

	'''Gets a connection to the Extrahop device,
	if that fails prints traceback and exits, else returns the connection object'''
	try:
		c = pyhop.Client(host=hostname,user=username,passwd=base64.b64decode(password))
	except Exception,e:
		print(e)
		traceback.print_exc(file=sys.stdout)
		sys.exit(1)

	if debug: print "we have connection. returning"
	return c


def flatten(l,results=None):  # [  123, [ 456,789]  ]
	if debug: print "inside recursive flatten def"
	'''	recusively flatens a list of lists into a single list'''
	if results is None:
		results = []
	for item in l:
		if isinstance(item,list):
			flatten(item,results)
		else:
			results.append(item)
	return results

def parse_count(k,v,oid):
	if debug: print "inside parse_count"
	if debug: print "args are:"
	if debug: print k
	if debug: print v
	if debug: print oid
	'''	returns a string of key=value for the count data type'''
	if debug: print "returning the following"
	if debug: print "oid=%d metric=%s %s=%d "%(oid,k,k,v)
	return "oid=%d metric=%s %s=%d "%(oid,k,k,v)


def parse_dataset(k,v,oid):
	if debug: print "inside parse_dataset"
	if debug: print "argvs are:"
	if debug: print k
	if debug: print v
	if debug: print oid
	
	'''	returns a string of key=value for the dataset data type	'''
	lines = []
	for item in v:
		line = "oid=%d metric=%s "%(oid,k) 
		for freq,val in item.iteritems():
			line += "%s=%d "%(freq,val)
		lines.append(line)
	
	if debug: print "returnign lines:"
	if debug: print lines
	
	return lines


def parse_topn_count(k,v,oid):
	if debug: print "inside parse_topn_count"
	'''	returns a string of key=value for the topn data type'''
	results = [] 
	for item in v:
		line = "oid=%d metric=%s %s=%d"%(oid,k,item['vtype'],item['value'])
		if item.has_key('key'):
			for key,val in item['key'].iteritems():
				line += " %s=%s "%(key,val)
			results.append(line)

	return results


def parse_snap(k,v,oid):
	if debug: print "inside parse_snap"
	'''	returns a string of key=value for the snap data type'''
	return "oid=%d metric=%s %s=%d "%(oid,k,k,v)

def parse_data(field_specs,results,oid,device):
	if debug: print "inside parse_data"
	if debug: print "args passed in are:"
	if debug: print field_specs
	if debug: print results
	if debug: print oid
	if debug: print device
	
	''' 
	there are 8 data type currently defined in the Extrahop API

	Name: count
	Description: Integer datatype
	Unit: 64-bit integer

	Name: snap
	Description: Integer datatype - the only difference in behavior when queried via getExStatsTotal function (see below)
	Unit: 64-bit integer

	Name: string
	Description: String datatype
	Unit: UTF-8 string

	Name: time
	Description: Integer datatype representing a time stamp
	Unit: UTC timestamp

	Name: dataset
	Description: A frequency table - for each entry, freq is the number of times value has been seen.
	Unit: 64-bit integer
	Field options (can be used with any of the methods below):
		:summary:field_name - 5-number summary
		:summary595:field_name - 5th and 95th percentile -- 'percentile5': 18.0, 'percentile95': 1230.0

	Name: topn_count
	Description: A set of count datatypes
	Unit: A set of 64-bit integers, keyed by a structure that can be anything: string, IP address, file name, etc.

	Name: topn_dset
	Description: Set of datasets.
	Unit: Set of datasets.
	Field options (can be used with any of the methods below):
		:summary:field_name - 5-number summary
		:summary595:field_name - 5th and 95th percentile

	Name: topn_snap
	Description: Set of snapsnot metrics.
	Unit: Set of snapshot metrics.

	Name: topn_sset
	Description: Set of sample sets.
	Unit: Set of sample sets.
	Additional calculations:
		Mean
		Sigma
		
	Name: topn_time
	Description: Set of times.
	Unit: Set of times.

	Name: topn_tset
	Description: Set of top-N sets.
	Unit: Set of sets.
	'''


	if not isinstance(results,pyamf.ASObject) or not results.has_key('stats'):
		if debug: print "was not instance of ASObject, returning"
		return 
	
	lines = []
	for item in results['stats']:
		if debug: print "item:"
		if debug: print item
		tmp = []
		time =  None
		for k,v in item.iteritems():
			if k in field_specs:
				if globals().has_key("parse_"+field_specs[k]):
					tmp.append(globals()["parse_"+field_specs[k]](k,v,oid))
				else:
					print "ERROR: found no def for type: %s"%field_specs[k]
				
			elif k == "time":
				time =  " time=%f"%(v)
	
		if time is not None:
			tmp = flatten(tmp)
			for line in tmp:
				line += time
				line += " device=%s "%device
				lines.append(line)
		
	for line in lines:
		print line



def main(username,password,hostname,interval,splunk_home):
	if debug: print "inside main def"
	'''
	main loop
	establishes a connections, runs API calls for metrics/nodes
	calls parse func to parse results and print to stdout
	closes connection
	'''
	if debug: print "establishing conn to ehop device"
	conn = get_connection(username,password,hostname)    

	if debug: print "attempting to open csv file"
	if debug: print os.path.join(splunk_home,'etc','apps','extrahop_metrics','lookups','ehm_selected_metrics.csv')
	
	with open(os.path.join(splunk_home,'etc','apps','extrahop_metrics','lookups','ehm_selected_metrics.csv'),'r') as fh:
		if debug: print "We have file handle"
		
		if len(fh.readlines()) > 0:
			if debug: print "we have readlines"
			fh.seek(0)
			reader  = csv.reader(fh)
			reader.next()
			for row in reader:
				if debug: print "row: %s"%row
				if row:
					device = row[0]
					field_spec = row[1].split(',')
					oid =  int(row[3])
			
					fs_dict = {}
					for item in field_spec:
						item = item.split(":")
						fs_dict[item[0]] = item[1]
					
			
					start_time = time.mktime(time.strptime((datetime.datetime.now() - relativedelta(minutes=1)).strftime('%Y-%m-%d %H:%M'), '%Y-%m-%d %H:%M'))
					start_time *= 1000
					options={'cycle':"fast",'topn_max':0}
					if debug: print "going to get_exstats"
					#if debug: print "extrahop.device."+device+", device, [("+oid+", "+start_time-(float(interval)*100)+", "+start_time+")],"+fs_dict.keys()+","+options
					result = conn.get_exstats( "extrahop.device."+device,
								   "device",
								   [(oid, start_time-(float(interval)*1000), start_time)], # one minute is 60,0000  (# of sec * 1000) [(oid,from,to)]
								   fs_dict.keys(),
								   options)
					if debug: print "done getting results"
					if result:
						if debug: print "calling parse data"
						parse_data(fs_dict,result,oid,device)

	conn.logout()
	sys.exit(0)

if __name__ == '__main__':
	if len(sys.argv) != 6:
		print "Not enough args to script! Expected: <script name>, <username>, <password>, <hostname>, interval, <splunk home>"
		sys.exit(1)
	else:
		if debug: print "calling main def"
		main(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4], sys.argv[5])
		if debug: print "returned from main def"
		
	sys.exit(0)


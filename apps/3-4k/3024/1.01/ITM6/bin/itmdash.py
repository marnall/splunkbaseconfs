import time, sys, csv, re, logging 

import splunk.Intersplunk as si 
from splunk import entity as en 

from itm6.dash import dash as itm6_dash 

def usage():
	return """Usage: | itmdash tems=<tems name> [endpoint=<endpoint>] [datasource=<datasource> [dataset=<dataset> [sourcetoken=<agent|msl> [properties=<properties>] [condition=<condition>] [field_format=<label|id>] [earliest=now latest=now]]]]"""


# set up logging suitable for splunkd consumption 
logging.root 
logging.root.setLevel(logging.DEBUG) 
formatter = logging.Formatter('%(levelname)s %(message)s') 
handler = logging.StreamHandler(stream=sys.stderr) 
handler.setFormatter(formatter) 
logging.root.addHandler(handler) 


results, dummyresults, settings = si.getOrganizedResults() 
session_key = settings.get('sessionKey', None) 
srinfo = {} 
messages = {} 

if 'infoPath' in settings: 
	with open(settings['infoPath'], 'r') as srinfofile: 
		inforeader = csv.reader(srinfofile) 
		header = inforeader.next() 
		data = inforeader.next() 
		srinfo = dict(zip(header, data)) 

# List accepted args here 
args = {
	'tems': 		{'value': '','set':False,'required': True,'requires': []},
	'endpoint':		{'value': 'items','set':False,'required': False,'requires': ['tems']},
	'datasource':	{'value': '','set':False,'required': False,'requires': ['tems']},
	'dataset':		{'value': '','set':False,'required': False,'requires': ['tems','datasource']},
	'sourcetoken':	{'value': [],'set':False,'required': False,'requires': ['tems','datasource','dataset']}, 
	'properties':	{'value': 'all','set':False,'required': False,'requires': ['tems','datasource','dataset','sourcetoken']},
	'condition':	{'value': '','set':False,'required': False,'requires': ['tems','datasource','dataset','sourcetoken']},
	'fieldformat':	{'value': 'label','set':False,'required': False,'requires': ['tems','datasource','dataset','sourcetoken']},
	'earliest':		{'value': '','set':False,'required': False,'requires': ['tems']},
	'latest':		{'value': '','set':False,'required': False,'requires': ['tems']}
}

# Parse args 
for arg in sys.argv: 
	match = re.match(r'\s*(\S+?)\s*=(.+)$', arg) 

	if match: 
		field = match.group(1) 
		value = match.group(2) 

		if field in args: 
			if type(args[field]['value']) is list: 
				args[field]['value'].append(value) 
				args[field]['set'] = True
			elif type(args[field]['value']) is str: 
				args[field]['value'] = value 
				args[field]['set'] = True
			else: 
				si.parseError(usage()) 
		else: 
			si.parseError(usage())

# Check if the args are OK
parseErr = False
for arg in args:
	if args[arg]['required'] and not args[arg]['value']:
		logging.error("Required arg %s not set" % arg)
		parseErr = True
	
	if args[arg]['set']:
		for req in args[arg]['requires']:
			if not args[req]['value']:
				logging.error("Arg %s requires %s" % (arg, req))
				parseErr = True

if parseErr:
	si.parseError(usage())

# get TEMS user/pass 
itm6env = en.getEntity(['admin', 'tems'], entityName=args['tems']['value'], namespace='ITM6', owner='nobody', sessionKey=session_key) 

# create itm dash object
id = ''
if 'domain_override' in itm6env:
	id = itm6env['domain_override']
else:
	id = itm6env['temsname']

dash = itm6_dash(id=id, username=itm6env['username'],password=itm6env['password'],hostname=itm6env['tepshost']) 

# interval is grabbed from SRInfo 
# Needs some work to accept various splunk time formats ie -1h, now, epoch 

interval = '' 
if args['earliest']['value'] or args['latest']['value']: 
	if args['earliest']['value'] == 'now' and args['latest']['value'] == 'now': 
		# dont set an interval.  Just get current data 
		pass 
else: 
	if '_startTime' in srinfo: 
		interval = dash.epoch_to_iso8601(float(srinfo['_startTime'])) 

	if '_endTime' in srinfo: 
		interval = interval +'/'+ dash.epoch_to_iso8601(float(srinfo['_endTime'])) 


# check if we are getting results or querying endpoints 
#results = [{'args': sys.argv}] 
results = [] 

if args['endpoint']['value'] == 'items' and args['dataset']['value'] and args['datasource']['value'] and args['tems']['value'] and args['properties']['value']: 

	# not all endpoints need a sourcetoken, but will insert a fake
	if args['dataset']['value'] in ['events','msys','mgrp','advice']: 
		args['sourcetoken']['value'] = ['__none__'] 

	# Get results from ITM one source at a time, slower but less mem/cpu intensive 
	for source in args['sourcetoken']['value']: 
		param = {} 

		if interval: 
			param['Time'] = interval 

		if source != '__none__':
			param['SourceToken'] = source 

		try: 
			data = dash.query_dataset(datasource=args['datasource']['value'], dataset=args['dataset']['value'], properties=args['properties']['value'], condition=args['condition']['value'], param=param ); 
		except Exception, e: 
			logging.error("Error getting sourcetoken %s: %s" % (source, e)); 
			continue 


		#results = [] 
		for event in data['items']: 
			output = { 
				'_raw': '', 
				'_time': '', 
				'host': itm6env['tepshost'], 
				'source': "%s:%s:%s" % (itm6env['temsname'], args['dataset']['value'], source), 
				'sourcetype': args['dataset']['value']
			} 
			for prop in event['properties']: 
				value = '' 

				# make sure we only use values that returned properly 
				if prop['valueState'] == 'ok': 
					# Use value, not display value for isodatetime fields 
					if prop['valueType'] == 'isodatetime': 
						value = prop['value'] 

						# Take the first time field we find and use it as the event timestamp 
						if not output['_time']: 
							output['_time'] = dash.iso8601_to_epoch(prop['value']) 
					else: 
						value = prop['displayValue'] 


					if output['_raw']: 
						output['_raw'] = output['_raw'] +';' 
					output['_raw'] = output['_raw'] + str(value) 
					output[prop[args['fieldformat']['value']]] = value 
			results.append(output) 
elif args['dataset'] or args['datasource'] or args['tems']: 

	data = {} 

	if args['dataset']['value'] and args['datasource']['value'] and args['tems']['value']: 
		data = dash.list_dataset(datasource=args['datasource']['value'], dataset=args['dataset']['value'], endpoint=args['endpoint']['value']) 
	elif args['datasource']['value'] and args['tems']['value']: 
		data = dash.list_datasets(datasource=args['datasource']['value']) 
	elif args['tems']['value']: 
		data = dash.list_datasources() 

	for event in data['items']: 
		output = { 
			'_time': time.time(), 
			'label': event['label'], 
			'id': event['id'], 
			'description':event['description'] 
		} 

		output['_raw'] = ','.join([str(output['label']), str(output['id']), str(output['description'])]) 

		results.append(output) 

else: 

	si.parseError(usage()) 

si.outputResults(results, messages=messages) 

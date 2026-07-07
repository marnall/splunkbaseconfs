import time, sys, csv, re, logging 
from datetime import datetime 

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import splunk.Intersplunk as si 
from splunk import entity as en 

from itm6.soap import soap as itm6_soap
from itm6.soap import sql as itm6_sql

def itm_to_epoch(datestring): 
	#1150916232221000
	return time.mktime(datetime.strptime(datestring, "1%y%m%d%H%M%S%f").timetuple()) 

def epoch_to_iso8601(timestamp): 
	return datetime.fromtimestamp(timestamp).isoformat() 

def usage(): 
	return """Usage: itmsoap tems=<tems> [sql=<sql> 
	| fields=<field,...> table=<table> at=<All|All Hubs|All Remotes|tems name> nodelist=<agent|msl> [clause=<where clause>] [timeout=<secs>] [timefield=<timefield>]
	| object=<object> target=<target> [attribute=<attribute,...>] [afilter=<condition,...>] [timefield=<timefield>]
	"""


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
	'at':'', 
	'fields':'*', 
	'table':'', 
	'nodelist': '', 
	'timeout':300, 
	'clause':'', 
	'tems':'', 
	'history':'N',
	'sql':'',
	'earliest':'', 
	'latest':'' ,
	'timefield':'',
	'object':'',
	'target':'',
	'attribute':'',
	'afilter':''
} 

# Parse args 
for arg in sys.argv: 
	match = re.match(r'\s*(\S+?)\s*=(.+)$', arg) 

	if match: 
		field = match.group(1) 
		value = match.group(2) 

		if field in args: 
			if type(args[field]) is list: 
				args[field].append(value) 
			elif type(args[field]) is str: 
				args[field] = value 
			else: 
				si.parseError(usage()) 
		else: 
			# Add parse error 
			si.parseError(usage()) 

			
# interval is grabbed from SRInfo 
# Needs some work to accept various splunk time formats ie -1h, now, epoch 

interval = '' 
if args['history'] == 'N': 
	# dont set an interval.  Just get current data 
	pass 
else:
	if '_startTime' in srinfo: 
		if args['afilter']:
				args['afilter'] = args['afilter'] + ','
		args['afilter'] = args['afilter'] + 'Write_Time;GT;'+str(int(float(srinfo['_startTime'])))

	if '_endTime' in srinfo:
		if args['afilter']:
				args['afilter'] = args['afilter'] + ','
		args['afilter'] = args['afilter'] + 'Write_Time;LT;'+str(int(float(srinfo['_endTime'])))		

itm6env = None
if args['tems']:
	# get TEMS user/pass 
	itm6env = en.getEntity(['admin', 'tems'], entityName=args['tems'], namespace='ITM6', owner='nobody', sessionKey=session_key)
else: 
	si.parseError(usage())

soap = itm6_soap(instance=itm6env['temsname'], username=itm6env['username'],password=itm6env['password'],hostname=itm6env['hostname'])

if args['at'] and args['fields'] and args['table'] and args['nodelist'] and args['timeout']:
	#build sql
	itm6sql = itm6_sql(
		action	= 'SELECT',
		at 		= args['at'],
		fields	= re.split('\s*,\s*', args['fields']),
		table	= args['table'],
		parma	= {
			'NODELIST':	args['nodelist'],
			'TIMEOUT':	args['timeout']
		}
	)

	if 'clause' in args:
		itm6sql.clause = args['clause']
		
	#AT can be given values that require us to lookup the TEMS to run at, these values start with All
	itm6sql.at = args['at']
	if itm6sql.at.startswith('All'):
		try:
			itm6sql.at = soap.get_tems_list(role=itm6sql.at)
		except Exception, e:
			logging.error("%s" % (e))
	args['sql'] = itm6sql.tostring()


# Run the sql request
if args['sql'] or args['table']:
	
	# Set default timestamp
	if not args['timefield']:
		if args['history'] == 'Y':
			args['timefield'] = 'WRITETIME'
		else:
			args['timefield'] = 'TIMESTAMP'

	try:
		response = soap.ct_get(sql=args['sql'])
	except Exception, e:
		logging.error("%s" % (e))
elif args['object']:

	# Set default timestamp
	if not args['timefield']:
		if args['history'] == 'Y':
			args['timefield'] = 'Write_Time'
		else:
			args['timefield'] = 'Timestamp'

	response = soap.ct_get(
		history=args['history'],
		object=args['object'],
		target=args['target'],
		attribute=re.split('\s*,\s*', args['attribute']),
		afilter=re.split('\s*,\s*', args['afilter'])
	)
else:
	si.parseError(usage()) 

#results = [{'args': sys.argv}] 
results = [] 

try:
	for row_elem in response.iterfind('DATA/ROW'):
		output = { 
			'_raw': '', 
			'_time': '', 
			'host': soap['hostname'], 
			'source': "%s" % (args['tems']), 
			'sourcetype': 'itmsoap' 
		}
		
		for elem in row_elem.iter():
			if elem.tag == 'ROW':
				continue

			if output['_raw']: 
				output['_raw'] = output['_raw'] +';' 
			output['_raw'] = output['_raw'] + str(elem.text) 
			output[elem.tag] = elem.text
			
			if elem.tag == args['timefield']:
				output['_time'] = itm_to_epoch(elem.text)
		results.append(output)
except Exception, e:
		logging.error("%s" % (e))
			
si.outputResults(results, messages=messages) 
#Copyright (C) 2014 Kieren Crossland
import sys, time, os, getopt
import logging
import argparse
import pprint
import re
import json
from splunk import entity as en
from itm6.dash import dash as itm6_dash

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

# set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

def run():
	logging.info('ITM6 Agent Data Collector is running')
	
	#get config
	config = get_config()

	#run query
	for tems in config['param']['tems']:		
		dash = itm6_dash(id=tems['id'], username=tems['username'],password=tems['password'],hostname=tems['tepshost'])
		
		param = {
			'SourceToken': config['param']['sourcetoken']
		}
		
		logging.info("Running query with datasource=%s; dataset=%s; properties=%s; conditions=%s; params=%s" % (config['param']['datasource'], config['param']['dataset'], config['param']['properties'], config['param']['condition'], param))
		try: 
			data = dash.query_dataset(
				datasource=config['param']['datasource'], 
				dataset=config['param']['dataset'], 
				properties=config['param']['properties'], 
				condition=config['param']['condition'], 
				param=param 
			); 
		except Exception, e: 
			logging.error("Error getting sourcetoken %s from TEPS %s: %s" % (config['param']['sourcetoken'],tems['tepshost'], e)); 
			continue 
		
		#create stream for output
		stream = ET.Element('stream')
		tree = ET.ElementTree(stream)
		timestr = str(time.time())
		
		logging.debug("%s" % json.dumps(data))
		for event in data['items']: 
			output = ''
			timeStr = ''
			
			for prop in event['properties']: 
				value = '' 

				# make sure we only use values that returned properly 
				if prop['valueState'] == 'ok': 
					# Use value, not display value for isodatetime fields 
					if prop['valueType'] == 'isodatetime': 
						value = prop['value'] 

						# Take the first time field we find and use it as the event timestamp 
						if not timeStr: 
							logging.debug("Setting timefield to %s" % prop[config['param']['fieldformat']])
							timeStr = str(dash.iso8601_to_epoch(prop['value']))
					else: 
						value = prop['displayValue'] 


					if output:
						output = output +', '
						# Remove spaces from long field names
					field = re.sub(r'\s', '_', prop[config['param']['fieldformat']]) 
					output = output + str(field) + '=' + str(value)

			event = ET.SubElement(stream, 'event')
			datax = ET.SubElement(event, 'data')
			datax.text = output
			timex = ET.SubElement(event, 'time')
			timex.text = timeStr
			
		tree.write(sys.stdout)
	
	#parse the results
	#output 

def get_config():
	config = {}
	
	try:
		logging.info('Parsing script configuration')
		# parse the config XML from stdin
		tree = ET.fromstring(sys.stdin.read())
		logging.debug(ET.tostring(tree).replace('\n','').replace('\r',''))
		
		for elem in tree:
			if elem.tag == 'configuration':
				continue
			if elem.text is None:
				continue
			#logging.debug(elem.tag, str(elem.text))
			config[elem.tag] = elem.text
		
		config['param'] = {}
		for elem in tree.iter('param'):
			if elem.text is None:
				continue
			print elem.attrib['name'], elem.text
			config['param'][elem.attrib['name']] = elem.text

	except Exception, e:
		raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)
	
	#tidy up some config values
	config['param']['properties'] = re.sub(r'\s', '', config['param']['properties']) 
	
	# Set optional params to None if they dont exist
	if 'condition' not in config['param']:
		config['param']['condition'] = None

	try:
	#get tems info from REST
		logging.debug('Getting TEMS configuration')
		if config['param']['tems'] != 'All':
			tems = en.getEntity(['admin', 'tems'], entityName=config['param']['tems'], namespace='ITM6', owner='nobody', sessionKey=config['session_key'])
			
			id = ''
			if 'domain_override' in tems:
				id = tems['domain_override']
			else:
				id = tems['temsname']
			
			config['param']['tems'] = [{
				'id':		id,
				'tepshost': tems['tepshost'],
				'username': tems['username'],
				'password': tems['password']
			}]
		else:
			config['param']['tems'] = []
			temsi = en.getEntities(['admin', 'tems'], sessionKey=config['session_key'], namespace='ITM6', owner="nobody")
			for tems in temsi:
				id = ''
				if 'domain_override' in temsi[tems]:
					id = temsi[tems]['domain_override']
				else:
					id = temsi[tems]['temsname']
				
				config['param']['tems'] = [{
					'id':		id,
					'tepshost': temsi[tems]['tepshost'],
					'username': temsi[tems]['username'],
					'password': temsi[tems]['password']
				}]

		#logging.debug("TEMS Username = " + str(tems['username']))
	except Exception, e:
		logging.fatal("Failed to get TEMS configuration: " + str(e))
		raise Exception, "Failed to get TEMS configuration: " + str(e)
	
	logging.debug('Returning config data')
	return config

def do_scheme():
	path=os.path.dirname(os.path.realpath(__file__))
	name=os.path.splitext(os.path.basename(os.path.realpath(__file__)))[0]
	with open("%s/%s.xml" % (path, name), 'r') as content_file:
		content = content_file.read()
	sys.stdout.write(content)

def validate_arguments():
	sys.exit(0)

if __name__ == '__main__':
	# get arguments
	parser = argparse.ArgumentParser()
	group = parser.add_mutually_exclusive_group(required=False)
	group.add_argument("--scheme", action="store_true", help="Display introspection scheme")
	group.add_argument("--validate-arguments", action="store_true", help="Validate arguments passed to this script from Splunk")
	args = parser.parse_args()
	if args.validate_arguments:
		validate_arguments()
	elif args.scheme:
		do_scheme()
	else:
		run()

	sys.exit(0)
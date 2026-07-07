#Copyright (C) 2014 Kieren Crossland
import sys, time, os, getopt
import logging
import argparse
import pprint
import re
from splunk import entity as en
from itm6.soap import soap as itm6_soap
from itm6.soap import sql as itm6_sql

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
	
	for tems in config['param']['tems']:
		soap = itm6_soap(instance=tems['instance'], username=tems['username'],password=tems['password'],hostname=tems['hostname'])
		
		logging.info("Running query with object=%s; attributes=%s; afilter=%s;" % (config['param']['object'], config['param']['attributes'], config['param']['afilter']))
		try:
			#run query
			response = soap.ct_get(
				object		= config['param']['object'],
				attributes	= config['param']['attributes'],
				afilter		= config['param']['afilter'],
				history		= 'NO'
			)
		except Exception, e:
			logging.error("%s" % (e))
			continue
		
		#create stream
		stream = ET.Element('stream')
		tree = ET.ElementTree(stream)
		timestr = str(time.time())
		#response.write(sys.stdout)
		
		logging.debug(ET.tostring(response.getroot()).replace('\n','').replace('\r',''))
		for row_elem in response.iterfind('DATA/ROW'):
			data = ""
			if len(config['param']['attributes']) > 0:
				row = {}
				for elem in row_elem.iter():
					if elem.tag == 'ROW':
						continue
					row[elem.tag] = elem.text

				for attribute in config['param']['attributes']:
					if attribute == 'ORIGINNODE':
						attribute = 'System_Name'
					logging.debug(data + attribute + '=' + row[attribute] + ', ')
					data = data + attribute + '=' + row[attribute] + ', '
			else:
				for elem in row_elem.iter():
					if elem.tag == 'ROW':
						continue
					logging.debug(data + elem.tag + '=' + elem.text + ', ')
					data = data + elem.tag + '=' + elem.text + ', '
				
			data = data[:-2]
			#data = ', '.join("%s=%r" % (key,val) for (key,val) in row.iteritems())
			event = ET.SubElement(stream, 'event')
			datax = ET.SubElement(event, 'data')
			datax.text = data
			timex = ET.SubElement(event, 'time')
			timex.text = timestr
			
		tree.write(sys.stdout)
	
	#parse the results
	#output 

def get_config():
	config = {}
	
	try:
		logging.debug('Parsing script configuration')
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
	if 'attributes' in config['param']:
		config['param']['attributes'] = re.sub(r'\s', '', config['param']['attributes']) 
		#config['param']['attributes'] = config['param']['attributes'].upper()
		config['param']['attributes'] = config['param']['attributes'].split(',')
	else:
		config['param']['attributes'] = []
	

	if 'afilter' in config['param']:
		config['param']['afilter'] = re.sub(r'\s*,\s*', ',', config['param']['afilter']) 
		config['param']['afilter'] = re.sub(r'\s*;\s*', ';', config['param']['afilter']) 
		if ',' in config['param']['afilter']:
			config['param']['afilter'] = config['param']['afilter'].split(',')
		else:
			config['param']['afilter'] = [config['param']['afilter']]
	else:
		config['param']['afilter'] = []

	try:
	#get tems info from REST
		logging.debug('Getting TEMS configuration')
		if config['param']['tems'] != 'All':
			tems = en.getEntity(['admin', 'tems'], entityName=config['param']['tems'], namespace='ITM6', owner='nobody', sessionKey=config['session_key'])
			config['param']['tems'] = [{
				'instance':	tems['temsname'],
				'hostname': tems['hostname'],
				'username': tems['username'],
				'password': tems['password']
			}]
		else:
			config['param']['tems'] = []
			temsi = en.getEntities(['admin', 'tems'], sessionKey=config['session_key'], namespace='ITM6', owner="nobody")
			for tems in temsi:
				config['param']['tems'].append({
					'instance':	temsi[tems]['temsname'],
					'hostname': temsi[tems]['hostname'],
					'username': temsi[tems]['username'],
					'password': temsi[tems]['password']
				})
		#logging.debug("TEMS Username = " + str(tems['username']))
	except Exception, e:
		logging.fatal("Failed to get TEMS configuration endpoint: " + str(e))
		raise Exception, "Failed to get TEMS configuration endpoint: " + str(e)
	
	logging.debug('Returning config data')
	return config

def do_scheme():
	path=os.path.dirname(os.path.realpath(__file__))
	name=os.path.splitext(os.path.basename(os.path.realpath(__file__)))[0]
	with open("%s/%s.xml" % (path, name), 'r') as content_file:
		content = content_file.read()
	sys.stdout.write(content)

def validate_arguments():
	
	#get config
	# try:
		# config = get_config()
	# except Exception, e:
		# print_error(e)
	
	#print_error('%s' % vars(config))
	
	# Run a test query to check we can contact ITM
	#for tems in config['param']['tems']:
		#soap = itm6_soap(instance=tems['instance'], username=tems['username'],password=tems['password'],hostname=tems['hostname'])
		#print_error(tems['instance'])
		# try:
			# #run query
			# response = soap.ct_get(
				# object		= 'Local_Time',
				# attributes	= 'Seconds',
				# afilter		= None,
				# history		= 'NO'
			# )
		# except Exception, e:
			# print_error(e)
			
	sys.exit(0)

	
# prints XML error data to be consumed by Splunk
def print_error(string):
	error = ET.Element('error')
	tree = ET.ElementTree(error)
	message = ET.SubElement(error, 'message')
	message.text = str(string)
	tree.write(sys.stdout)
	sys.exit(1)
	

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
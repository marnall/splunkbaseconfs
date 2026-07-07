#Copyright (C) 2014 Kieren Crossland
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
	logging.debug('ITM6 Agent Data Collector is running')
	
	#get config
	config = get_config()		

	#build sql
	itm6sql = itm6_sql(
		action	= 'SELECT',
		at 		= config['param']['at'],
		fields	= config['param']['fields'],
		table	= config['param']['table'],
		parma	= {
			'NODELIST':	config['param']['system'],
			'TIMEOUT':	config['param']['timeout']
		}
	)
	
	if 'clause' in config['param']:
		itm6sql.clause = config['param']['clause']

	#run query
	
	for tems in config['param']['tems']:
		soap = itm6_soap(instance=tems['instance'], username=tems['username'],password=tems['password'],hostname=tems['hostname'])
		
		#AT can be given values that require us to lookup the TEMS to run at, these values start with All
		itm6sql.at = config['param']['at']
		if itm6sql.at.startswith('All'):
			try:
				itm6sql.at = soap.get_tems_list(role=itm6sql.at)
			except Exception, e:
				logging.error("%s" % (e))
				continue

		logging.debug("Running SQL on %s: %s" %(tems['instance'], itm6sql.tostring()))
		
		try:
			response = soap.ct_get(sql=itm6sql.tostring())
		except Exception, e:
			logging.error("%s" % (e))
			continue
		
		#create stream
		stream = ET.Element('stream')
		tree = ET.ElementTree(stream)
		timestr = str(time.time())

		logging.debug(ET.tostring(response.getroot()).replace('\n','').replace('\r',''))
		try:
			for row_elem in response.iterfind('DATA/ROW'):
				data = ""
				for elem in row_elem.iter():
					if elem.tag == 'ROW':
						continue
					data = data + str(elem.tag) + '=' + str(elem.text) + ', '

				data = data[:-2]
				event = ET.SubElement(stream, 'event')
				datax = ET.SubElement(event, 'data')

				datax.text = data
				timex = ET.SubElement(event, 'time')
				timex.text = timestr
		except Exception, e:
			raise Exception, "Error reading ITM response from %s: %s" % (tems['instance'], str(e))
			
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
	config['param']['fields'] = re.sub(r'\s', '', config['param']['fields']) 
	config['param']['fields'] = config['param']['fields'].upper()
	config['param']['fields'] = config['param']['fields'].split(',')

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
	sys.exit(0) #cant do this until soap is working
	#path=os.path.dirname(os.path.realpath(__file__))
	#with open(path+'/test_validate.xml', 'r') as content_file:
	#	content = content_file.read()
	#tree = ET.ElementTree(ET.fromstring(content))
	#for elem in tree.iterfind('items/item'):
	#	print elem.tag, elem.attrib

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
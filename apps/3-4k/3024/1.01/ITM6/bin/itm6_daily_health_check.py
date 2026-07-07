#Copyright (C) 2014 Kieren Crossland
import sys, time, os, getopt
import logging
import argparse
import pprint
import re
import json
from splunk import entity as en
from itm6.soap import soap as itm6_soap
from itm6.soap import sql as itm6_sql
import splunk.rest as rest

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
	
	start_time = time.time()
	
	#get config
	config = get_config()
	
	#create stream for splunk output
	streamEl = ET.Element('stream')
	streamET = ET.ElementTree(streamEl)
	timestr = str(time.time())
	
	# Store failed nodes
	fail = {}
	
	for tems in config['param']['tems']:
		
		logging.info("Collecting from %s (%s)" % (tems['instance'], tems['hostname']))
		
		# Create soap object for TEMS
		soap = itm6_soap(instance=tems['instance'], username=tems['username'],password=tems['password'],hostname=tems['hostname'])
		
		# get node status for this tems
		logging.info("Getting node list")
		try:
			node_status = soap.ct_get(sql="SELECT NODE,THRUNODE,O4ONLINE FROM O4SRV.INODESTS")
			logging.debug(ET.tostring(node_status.getroot()).replace('\n','').replace('\r',''))
		except Exception, e:
			logging.error("%s" % (e))
			continue
	
		logging.info("Getting MSL list")
		try:
			# Get distinct list of MSLS
			msls = soap.ct_get(sql="SELECT NODELIST,COUNT(NODE) FROM O4SRV.TNODELST WHERE NODETYPE='M' GROUP BY NODELIST")
			logging.debug(ET.tostring(msls.getroot()).replace('\n','').replace('\r',''))
		except Exception, e:
			logging.error("%s" % (e))
			continue

		# Loops through each MSL
		for mslEl in msls.iterfind('./DATA/ROW/NODELIST'):
			msl = mslEl.text
			
			# Skip MSLS not starting with *
			if not msl.startswith('*'):
				continue
			
			# Get agent list for this MSL
			logging.info("Getting node list for MSL %s" % msl)
			try:
				nodes = soap.ct_get(sql="SELECT NODE FROM O4SRV.TNODELST WHERE NODETYPE='M' AND NODELIST ='%s'" % msl)
				logging.debug(ET.tostring(nodes.getroot()).replace('\n','').replace('\r',''))
			except Exception, e:
				logging.error("%s" % (e))
				continue
			
			logging.info("Running Op Log test for agents in msl %s connected to %s" % (str(msl), tems['instance']))
			
			# Store response for KV 
			# This will be updated in per msl/tems batches
			kv = []
			
			# Run Query against all the TEMS
			try:
				op_result = soap.ct_get(sql="SELECT ORIGINNODE,COUNT(MSGTEXT) FROM O4SRV.OPLOG AT ('%s') WHERE SYSTEM.PARMA('NODELIST','%s',%s) AND SYSTEM.PARMA('TIMEOUT','300',3)" % ("','".join(soap.get_tems_list()), msl, str(len(msl))))
				logging.debug(ET.tostring(op_result.getroot()).replace('\n','').replace('\r',''))
			except Exception, e:
				logging.error("%s" % (e))
				continue
			
			# Prepare the results
			for nodeEl in nodes.iterfind('./DATA/ROW/NODE'):
				node = nodeEl.text
				
				node_statusEl = node_status.findall("./DATA/ROW[NODE='%s']" % node)
				if node_statusEl[0] is not None:
					status = node_statusEl[0].findtext('./O4ONLINE')
					thrunode = node_statusEl[0].findtext('./THRUNODE')
				
				if len(op_result.findall("./DATA/ROW/[System_Name='%s']" % node)) == 0:
					# Failed					
					if status == 'N':
						logging.info("%s is Offline" % node)
						#Node offline so set to failed
						eventEl = ET.SubElement(streamEl, 'event')
						dataEl = ET.SubElement(eventEl, 'data')
						dataEl.text = "agent=%s, oplog_result=Offline, online=%s, hub=%s, remote=%s" % (node,status,tems['instance'],thrunode)
						timeEl = ET.SubElement(eventEl, 'time')
						timeEl.text = timestr
						
						kv.append({'_key':node, 'hub':tems['instance'], 'remote':thrunode, 'oplog_result': 'Offline', 'online': status, 'last_run': start_time})
					else:
						# Add failure to retry list
						logging.info("%s did not respond.  Adding to retry list" % node)
						if thrunode not in fail:
							fail[thrunode] = []
						
						fail[thrunode].append(node)
						
				else:
					#Passed	
					logging.debug("%s Responded" % node)
					eventEl = ET.SubElement(streamEl, 'event')
					dataEl = ET.SubElement(eventEl, 'data')
					dataEl.text = "agent=%s, oplog_result=Pass, online=Y, hub=%s" % (node, tems['instance'])
					timeEl = ET.SubElement(eventEl, 'time')
					timeEl.text = timestr

					kv.append({'_key':node, 'hub':tems['instance'], 'remote':thrunode, 'oplog_result': 'Pass', 'online':'Y', 'last_run': start_time})
			
			# Update health status KV store for this MSL/TEMS
			if len(kv) > 0:
				logging.info("Updating itm_agent_health KV Store")
				logging.debug(json.dumps(kv))
				response, content = rest.simpleRequest('/servicesNS/nobody/ITM6/storage/collections/data/itm_agent_health/batch_save',sessionKey=config['session_key'],method='POST',jsonargs=json.dumps(kv))
			
		# Re-run any failures to make sure they really failed
		for thrunode in fail:			
			kv = []
			
			for node in fail[thrunode]:
				logging.info("Re-running test on %s" % node)
				try:
					op_result = soap.ct_get(sql="SELECT ORIGINNODE,COUNT(MSGTEXT) FROM O4SRV.OPLOG AT ('%s') WHERE SYSTEM.PARMA('NODELIST','%s',%s) AND SYSTEM.PARMA('TIMEOUT','300',3)" % (thrunode, node, len(node)))
				except Exception, e:
					logging.error("%s" % (e))
					continue
				
				if len(op_result.findall("./DATA/ROW/[System_Name='%s']" % node)) == 0:
					logging.info("%s failed" % node)
					# Failed
					#Node offline so set to failed
					eventEl = ET.SubElement(streamEl, 'event')
					dataEl = ET.SubElement(eventEl, 'data')
					dataEl.text = "agent=%s, oplog_result=Fail, online=N, hub=%s, remote=%s" % (node, tems['instance'], thrunode)
					timeEl = ET.SubElement(eventEl, 'time')
					timeEl.text = timestr
	
					kv.append({'_key':node, 'hub':tems['instance'], 'remote':thrunode, 'oplog_result': 'Fail', 'online': 'Y', 'last_run': start_time})
				else:
					#Passed	
					logging.debug("%s Responded" % node)
					eventEl = ET.SubElement(streamEl, 'event')
					dataEl = ET.SubElement(eventEl, 'data')
					dataEl.text = "agent=%s, oplog_result=Pass, online=Y, hub=%s, remote=%s" % (node, tems['instance'], thrunode)
					timeEl = ET.SubElement(eventEl, 'time')
					timeEl.text = timestr
					
					kv.append({'_key':node, 'hub':tems['instance'], 'remote':thrunode, 'oplog_result': 'Pass', 'online': 'Y', 'last_run': start_time})
				
				# Update these agents in the KV store
				logging.info("Updating itm_agent_health KV Store")
				logging.debug(json.dumps(kv))
				response, content = rest.simpleRequest('/servicesNS/nobody/ITM6/storage/collections/data/itm_agent_health/batch_save',sessionKey=config['session_key'],method='POST',jsonargs=json.dumps(kv))
		
		# Output for indexing
		logging.info("Writing to std out")
		streamET.write(sys.stdout)


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

	logging.info("Parsed XML script configuration")	
		
	try:
	#get tems info from REST
		logging.info('Getting configuration for TEMS %s, %s, %s' % (config['param']['tems'], config['session_key'], config))
		if config['param']['tems'] != 'All':
			logging.info("Getting tems entities")
			tems = en.getEntity(['admin', 'tems'], entityName=config['param']['tems'], namespace='ITM6', owner='nobody', sessionKey=config['session_key'])
			logging.info("Grabbed entity for TEMS %s" % tems['temsname'])
			config['param']['tems'] = [{
				'instance':	tems['temsname'],
				'hostname': tems['hostname'],
				'username': tems['username'],
				'password': tems['password']
			}]
		else:
			config['param']['tems'] = []
			logging.info("Getting tems entity")
			temsi = en.getEntities(['admin', 'tems'], sessionKey=config['session_key'], namespace='ITM6', owner="nobody")
			for tems in temsi:
				logging.info("Grabbed entity for TEMS %s" % temsi[tems]['temsname'])
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

	#get config
	#try:
	#	config = get_config()
	#except Exception, e:
	#	print_error(e)

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
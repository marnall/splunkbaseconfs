# encoding = utf-8

import os
import sys
import time
import datetime
import json
import hashlib
import jbxapi
import copy

def fltr(node, vals):
	if isinstance(node, dict):
		retVal = {}
		for key in node:
			if key in vals:
				retVal[key] = copy.deepcopy(node[key])
			elif isinstance(node[key], list) or isinstance(node[key], dict):
				child = fltr(node[key], vals)
				if child:
					retVal[key] = child
		if retVal:
			 return retVal
		else:
			 return None
	elif isinstance(node, list):
		retVal = []
		for entry in node:
			child = fltr(entry, vals)
			if child:
				retVal.append(child)
		if retVal:
			return retVal
		else:
			return None

def fltr_del(node, vals):
	if isinstance(node, dict):
		retVal = {}
		for key in node:
			if key not in vals:
				if isinstance(node[key], list) or isinstance(node[key], dict):
					child = fltr_del(node[key], vals)
					if child:
						retVal[key] = child
				else:
					retVal[key] = copy.deepcopy(node[key])
		if retVal:
			 return retVal
		else:
			 return None
	elif isinstance(node, list):
		retVal = []
		for entry in node:
			child = fltr_del(entry, vals)
			if child:
				retVal.append(child)
		if retVal:
			return retVal
		else:
			return None
def merge_arrays(node, helper):
	if isinstance(node, dict):
		retVal = copy.deepcopy(node)
		if '@isArray' in node:
			for key in node:
				if isinstance(node[key], list):
					merged = {}

					for d in node[key]:
						if isinstance(d, dict):
							merged.update(d)
					if merged:
						retVal[key] = merged
		else:
			for key in node:
				retVal[key] = merge_arrays(node[key], helper)
		return retVal
	else:
		return node

def validate_input(helper, definition):
	"""Implement your own validation logic to validate the input stanza configurations"""

	pass

def collect_events(helper, ew):
	opt_api_url = helper.get_arg('api_url')
	opt_api_key = helper.get_arg('api_key')
	minimum_web_id = helper.get_arg('minimum_web_id')
	opt_ssl = helper.get_arg('verify_ssl')
	small_report = helper.get_arg('small_report')
	http_https_proxy = helper.get_arg('http_https_proxy')
	
	proxies = None
	
	if http_https_proxy != None and len(http_https_proxy) != 0:
		proxies = {
			 "http": http_https_proxy,
			 "https": http_https_proxy,
		}
	
	jbx = jbxapi.JoeSandbox(apikey=opt_api_key, apiurl=opt_api_url, verify_ssl=opt_ssl, proxies=proxies)

	min_id = 0
	try:
		min_id = int(minimum_web_id)
	except:
		min_id = 0
		
		
	jbx_inst = hashlib.md5(opt_api_url.encode('utf-8')).hexdigest()[0:20] 

	last_web_id = 0
	last_key = jbx_inst + "last"

	# Get the web id of the last not yet finished analysis
	try:
		last_web_id = int(helper.get_check_point(last_key))
	except:
		pass
		
	helper.log_info("Last web ID is: " + str(last_web_id))
		
	# Get all analysis
	analysis_list = jbx.analysis_list()
	
	smallest_notfinished_webid = -1
	
	for analysis in analysis_list:
		webid = int(analysis['webid'])

		if webid < min_id or webid < last_web_id:
		
			helper.log_info("Skip web id: " + str(webid))
		
			continue
		
		# First is the most recent, highest webid
		if smallest_notfinished_webid == -1:
			smallest_notfinished_webid = webid

		# Make key shorter
		report_key = str(webid) + jbx_inst

		state = helper.get_check_point(report_key)
		helper.log_debug("Key: " + report_key + " State: " + str(state))
		
		if state != 'downloaded':
		
			helper.log_info("Check finished")
		
			#download report and generate event
			info = jbx. analysis_info(webid=webid)
			
			helper.log_info("info: "+ str( info))
			
			if info['status'] == 'finished':
			
				helper.log_info("Finished " + str(webid))

				for run_id in range(len(info['runs'])):
					try:
						name, data = jbx.analysis_download(webid=webid, type='lightjsonfixed', run=run_id)
						report = json.loads(data.decode('utf8'))['analysis']

						report = fltr_del(report, ['$', '@isArray'])
						report['info'] = copy.deepcopy(info)
						del report['info']['runs']
						report['info']['run'] = info['runs'][run_id]
						
						if "behaviorgraph" in report:
							del report['behaviorgraph']
						if "similarsiggraph" in report:
							del report['similarsiggraph']
						
						if small_report:
							if "behavior" in report:
								del report['behavior']
							if "eventlog" in report:
								del report['eventlog']
								
						datajson = json.dumps(report, sort_keys=True)
						event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=datajson)
						ew.write_event(event)
					except:
						helper.log_warning("Unable to download resource: %s" % sys.exc_info()[0])
						
						
				helper.save_check_point(report_key, 'downloaded')
				
			else:
				# Store the smallest not yet finished analysis
				if webid < smallest_notfinished_webid:
					smallest_notfinished_webid = webid
					
	# Store the smallest not yet finished analysis
	helper.save_check_point(last_key, str(smallest_notfinished_webid))

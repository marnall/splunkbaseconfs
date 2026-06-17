#!/opt/splunk/bin/python
############################################################
#
# Extract one or more agent keys from the OSSEC server
# given agent name and/or id
#
############################################################
import sys
import splunk.Intersplunk as si
sys.path.append('../3rdparty/pexpect-2.3')
from pyOSSEC import *
import base64


SCRIPT_ARGS = {
	'ossec_server':	'',
	'agent_name':	None,
	'agent_id':	'',
	'format':	'base64'
}


args = parse_args(sys.argv, SCRIPT_ARGS)
try:
	results,dummyresults,settings = si.getOrganizedResults()
	row = args
	ids = []

	try:
		ossec = OSSECServer(args['ossec_server'])

		if args['agent_name'] != None: 
			ids += ossec.find_agent_ids(args['agent_name'])

		if args['agent_id'] != None and args['agent_id'] != '' and args['agent_id'] not in ids:
			ids.insert(0, args['agent_id'])

		for id in ids:
			row = {}

			try:
				key = ossec.extract_key(id)

				decoded = base64.b64decode(key)
				parts = decoded.split()
				row['agent_id'] = parts[0]
				row['agent_name'] = parts[1]
				row['agent_ip'] = parts[2]

				if args['format'] == 'raw':
					row['key'] = decoded
				else:
					row['key'] = key

			except OSSECError:
				# Errors from the OSSEC interface will be treated as failures
				# and reported in tabular format. Other errors will still bubble
				# up to Splunk's traditional reporting method.
				row = args
				row['status']  = 'Error'
				row['type']    = sys.exc_info()[0].__name__
				row['message'] = sys.exc_info()[1]

			results.append ( row )

	except:
		row = args
		row['status']  = 'Error'
		row['type']    = sys.exc_info()[0].__name__
		row['message'] = sys.exc_info()[1]


except:
	import traceback
	stack = traceback.format_exc()
	results = si.generateErrorResults("Error : Traceback: " + str(stack))

si.outputResults(results)

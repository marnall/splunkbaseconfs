#!/opt/splunk/bin/python
############################################################
#
# List all agents on the OSSEC server
#
############################################################
import sys
import splunk.Intersplunk as si
from pyOSSEC import *


# Extract user id for audit purposes...
##results, dummyresults, settings = si.getOrganizedResults()
##user = settings.get("authString", None)
##if user != None:
##	pos = user.find('<userId>') + 8
##	user = user[pos:]
##	pos = user.find('</userId>')
##	user = user[:pos]

SCRIPT_ARGS = {
        'ossec_server':  ''
}


args = parse_args(sys.argv, SCRIPT_ARGS)
try:
	results = []

	try:
		ossec = OSSECServer(args['ossec_server'])
		row = args
		ossec.cache_agents()

		for (agent_id, agent_name, agent_ip) in ossec.agents:
			row = {
				'agent_name':   agent_name,
				'agent_ip':     agent_ip,
				'agent_id':     agent_id
			}
			results.append(row)

		if len(results) == 0:
			row['status'] = 'Success'
			row['message'] = 'No agents found.'
			results.append(row)

	except OSSECError:
		# Errors from the OSSEC interface will be treated as failures
		# and reported in tabular format. Other errors will still bubble
		# up to Splunk's traditional reporting method.
		row = {
			'ossec_server':  args['ossec_server'],
			'status':        'Error',
	                'type':          sys.exc_info()[0].__name__,
        	        'message':       sys.exc_info()[1]
		}
		results = [ row ]


except:
	import traceback
	stack = traceback.format_exc()
	results = si.generateErrorResults("Error : Traceback: " + str(stack))

si.outputResults(results)

#!/opt/splunk/bin/python
############################################################
#
# Add a new agent record to the OSSEC server
#
############################################################
import sys
import splunk.Intersplunk as si
sys.path.append('../3rdparty/pexpect-2.3')
from pyOSSEC import *



SCRIPT_ARGS = {
	'agent_name':	None,
	'agent_ip':	None,
	'agent_id':	'',
	'ossec_server':	''
}



args = parse_args(sys.argv, SCRIPT_ARGS)
try:
	results,dummyresults,settings = si.getOrganizedResults()
	row = args

	try:
		ossec = OSSECServer(args['ossec_server'])

		row['agent_id'] = ossec.add_agent(args['agent_name'], args['agent_ip'], args['agent_id'])

		row['message']  = 'Agent added'
		row['status']   = 'Success'

        except OSSECError:
		# Errors from the OSSEC interface will be treated as failures
		# and reported in tabular format. Other errors will still bubble
		# up to Splunk's traditional reporting method.
		row['status']  = 'Error'
		row['type']    = sys.exc_info()[0].__name__
		row['message'] = sys.exc_info()[1]

	results = [ row ]


except:
	import traceback
	stack = traceback.format_exc()
	results = si.generateErrorResults("Error : Traceback: " + str(stack))

si.outputResults(results)

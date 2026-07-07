import sys, json
import urllib2
import re

def send_cem_message(input):
	params = dict()
	config = input.get('configuration')
	url = config.get('cem_webhook')
	
	# create outbound JSON message body
	params['search_name'] = input.get('search_name')
	params['app'] = input.get('app')
	params['owner'] = input.get('owner')
	params['results_link'] = input.get('results_link')
	params['sid'] = input.get('sid')
	params['result'] = input.get('result')
	
	resname = config.get('cem_resource_name')
	if resname is None:
		params['resourceName'] = ""
	else:
		params['resourceName'] = resname
	
	evttype = config.get('cem_event_type')
	if evttype is None:
		params['eventType'] = ""
	else:
		params['eventType'] = evttype
	
	custom = config.get('cem_custom')
	if custom is None:
		params['custom'] = ""
	else:
		params['custom'] = custom
	
	summary = config.get('cem_summary')
	if summary is None:
		params['summary'] = ""
	else:
		params['summary'] = summary
		
	params['resourceType'] = config.get('cem_resource_type')
	params['severity'] = config.get('cem_severity')
	
	body = json.dumps(params)
	
	req = urllib2.Request(url, body, {"Content-Type": "application/json"})
	try:
		res = urllib2.urlopen(req)
		body = res.read()
        	print >> sys.stderr, "INFO IBM CEM Webhook responded with HTTP status=%d" % res.code
        	print >> sys.stderr, "DEBUG IBM CEM Webhook response: %s" % json.dumps(body)
        	return 200 <= res.code < 300
    	except urllib2.HTTPError, e:
        	print >> sys.stderr, "ERROR Error sending message: %s" % e
        	return False
if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        	payload = json.loads(sys.stdin.read())
        	if not send_cem_message(payload):
            		print >> sys.stderr, "FATAL Sending the IBM CEM message failed"


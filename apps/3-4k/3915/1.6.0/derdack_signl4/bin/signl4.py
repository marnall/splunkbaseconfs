import sys
import json
import requests
import csv
import gzip
from collections import OrderedDict


def send_webhook_request(s4teamsecret, body, user_agent=None):

	url = 'https://connect.signl4.com/webhook/' + str(s4teamsecret)

	print("INFO Sending POST request to url=%s with size=%d bytes payload" % (url, len(body)), sys.stderr)
	print("INFO Body: %s" % (body), sys.stderr)
	
	#jsonBody = json.loads(body)
	#jsonBody['X-S4-Service'] = 'Splunk'
	
	try:
		res = requests.post(url, data=body, headers={"Content-Type": "application/json", "User-Agent": user_agent})
		if 200 <= res.status_code < 300:
			print("INFO Webhook receiver responded with HTTP status=%d" % (res.status_code), sys.stderr)
			return True
		else:
			print("ERROR Webhook receiver responded with HTTP status=%d" % (res.status_code), sys.stderr)
			return False
	except requests.ConnectionError as e:
		print("ERROR Error sending webhook request: %s" % (e), sys.stderr)
	except ValueError as e:
		print("ERROR Invalid URL: %s" % (e), sys.stderr)
	return False

	
	

if __name__ == "__main__":
	if len(sys.argv) < 2 or sys.argv[1] != "--execute":
		print("FATAL Unsupported execution mode (expected --execute flag)", sys.stderr)
		sys.exit(1)
	try:
		settings = json.loads(sys.stdin.read())
		
		s4category = settings['configuration'].get('category')
		s4teamsecretSearch = settings['configuration'].get('teamSecretSearch')
		s4teamsecretSetup = settings['configuration'].get('teamSecret')
		s4teamsecret = s4teamsecretSetup
		
		if s4teamsecretSearch not in [None, '']:
			s4teamsecret = s4teamsecretSearch
					
		body = OrderedDict(
			search_name=settings.get('search_name'),
			result=settings.get('result'),
			sid=settings.get('sid'),
			app=settings.get('app'),
			owner=settings.get('owner'),
			results_link=settings.get('results_link')			
		)

		body['X-S4-Service'] = s4category
		body['X-S4-SourceSystem'] = 'Splunk'

		# user_agent = settings['configuration'].get('user_agent', 'Splunk')
		
		if not send_webhook_request(s4teamsecret, json.dumps(body), 'Splunk'):
			sys.exit(2)
	except Exception as e:
		print("ERROR Unexpected error: %s" % (e), sys.stderr)
		sys.exit(3)

import json
import os
import requests
import sys
import urllib
import urllib.request
import gzip
import csv
import base64
from urllib.request import urlopen

sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','hubspot_app','lib'))

import splunklib.client as client

def getCredentials(sessionKey):

    myapp = 'hubspot_app'
    service = client.Service(token=sessionKey, app=myapp)
    pws = service.storage_passwords

    if len(pws) < 1:
        raise Exception("Could not get api_key")

    return service.storage_passwords.list()[0].content["clear_password"]

def send_notification(payload,api_key):


	hs_url = "https://api.hubapi.com/crm-objects/v1/objects/tickets?hapikey="
	hs_eng = "https://api.hubapi.com/engagements/v1/engagements?hapikey="

	settings = payload.get('configuration')
	message_type = settings.get('message_type')
	ticket_notes = settings.get('notes')
	pipeline = settings.get('pipeline')
	view_report = payload.get('results_link')
	results_file = payload.get('results_file')
	api_endpoint = hs_url + api_key
	eng_api_endpoint = hs_eng + api_key
	search_name = payload.get('search_name')
	entity_display_name = settings.get('entity_display_name')

	pipeline_stage=int(pipeline) + 1


	entity_id = "Splunk Alert: " + search_name


	hub_payload=[{
	"name": "subject",
	"value": entity_id
	},
	{
	"name": "hs_ticket_priority",
	"value": message_type
	},
	{
	"name": "content",
	"value": view_report
	},
	{
	"name": "hs_pipeline",
	"value": pipeline
	},
	{
	"name": "hs_pipeline_stage",
	"value": pipeline_stage
	}]

	body = json.dumps(hub_payload).encode('utf-8')
	req = urllib.request.Request(api_endpoint, body, {"Content-Type": "application/json"})

	try:
		res = urlopen(req)
		body = res.read()
		body_str = json.loads(body)
		ticket_id = body_str['properties']['hs_ticket_id']['value']

		eng_payload = {
    		"engagement": {
    			"active": "true",
        		"type": "NOTE",
    		},
    		"associations": {
				"ticketIds": [ticket_id]
    		},
    		"metadata": {
        		"body": ticket_notes
    		}
		}

		body2 = json.dumps(eng_payload).encode('utf-8')
		req2 = urllib.request.Request(eng_api_endpoint, body2, {"Content-Type": "application/json"})
		res2 = urlopen(req2)
		return 200 <= res.code < 300
	except urllib.error.HTTPError as e:
		print("ERROR Error sending message")
		return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # read session key sent from splunkd
        jsonInput = sys.stdin.readline().strip()
        jsonObj = json.loads(jsonInput)
        sessionKey = jsonObj["session_key"]

        if len(sessionKey) == 0:
            sys.stderr.write("Did not receive a session key from splunkd. ")
            exit(2)

        # get api key
        api_key = getCredentials(sessionKey)
        success = send_notification(jsonObj, api_key)

        if not success:
            print("FATAL Failed trying to send notification")
            sys.exit(2)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)")
        sys.exit(1)

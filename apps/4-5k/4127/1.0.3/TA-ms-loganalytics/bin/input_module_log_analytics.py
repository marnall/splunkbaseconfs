import adal
import datetime
import json
import os
import sys
import time
import requests
from splunklib.modularinput import *

def validate_input(helper, definition):
	inputs=helper.get_input_stanza()
	for input_name, input_item in inputs.iteritems():
		start_date = str(input_item["start_date"])
		try:
			valid_date = datetime.datetime.strptime(start_date, '%d/%m/%Y %H:%M:%S')
		except ValueError:
			helper.log_error("Start date must be in the format of dd/mm/yyyy hh:mm:ss")
	pass

def collect_events(helper, ew):

	# Go through each input for this modular input
	inputs=helper.get_input_stanza()
	for input_name, input_item in inputs.iteritems():
		# Get the values, cast them as floats
		resource_group = str(input_item["resource_group"])
		workspace = str(input_item["workspace_id"])
		query = str(input_item["log_analytics_query"])
		subscription_id = str(input_item["subscription_id"])
		tenant_id = str(input_item["tenant_id"])
		application_id = str(input_item["application_id"])
		application_key = str(input_item["application_key"])
		event_lag = int(float(input_item["event_delay_lag_time"]))

		# Date and delta
		if helper.get_check_point(input_name):
			start_datetime = datetime.datetime.strptime(helper.get_check_point(input_name),'%d/%m/%Y %H:%M:%S')
		else:
			start_datetime = datetime.datetime.strptime(str(input_item['start_date']),'%d/%m/%Y %H:%M:%S')
		now = datetime.datetime.utcnow() - datetime.timedelta(minutes=event_lag)
		now_dt = now.replace(microsecond=0)

		# URLs for authentication
		authentication_endpoint = 'https://login.microsoftonline.com/'
		resource  = 'https://api.loganalytics.io/'

		# Get access token
		context = adal.AuthenticationContext('https://login.microsoftonline.com/' + tenant_id)
		token_response = context.acquire_token_with_client_credentials('https://api.loganalytics.io/', application_id, application_key)
		access_token = token_response.get('accessToken')

		# Add token to header
		headers = {
			"Authorization": 'Bearer ' + access_token,
			"Content-Type":'application/json'
		}

		# URLs for retrieving data
		uri_base = 'https://api.loganalytics.io/'
		uri_api = 'v1/'
		uri_workspace = 'workspaces/' + workspace + '/'
		uri_area = "query"
		uri = uri_base + uri_api + uri_workspace + uri_area

		# Build search parameters from query details
		search_params = {
			"query": query,
			"timespan": start_datetime.strftime('%Y-%m-%dT%H:%M:%S') + '/' + now_dt.strftime('%Y-%m-%dT%H:%M:%S')
		}

		# Send post request
		response = requests.post(uri,json=search_params,headers=headers)

		# Response of 200 if successful
		if response.status_code == 200:
			# If debug, log event
			helper.log_debug('OMSInputName="' + str(input_name) + '" status="' + str(response.status_code) + '" step="Post Query" search_params="' + str(search_params) + "'")
			# Parse the response to get the ID and status
			data = response.json()
		else:
			# Request failed
			helper.log_error('OMSInputName="' + str(input_name) + '" status="' + str(response.status_code) + '" step="Post Query" response="' + str(response.text) + '"')
			
		#Building proper json format from original request
		#First loop checks how many events returned is in response
		for i in range(len(data["tables"][0]["rows"])):
			data1 = "{"
			#This nested loop goes through each field, in each event, and concatenates the field name to the field value
			for n in range(len(data["tables"][0]["rows"][i])):
				field = str(data["tables"][0]["columns"][n]["name"])
				value = str(data["tables"][0]["rows"][i][n]).replace('"',"'").replace("\\", "\\\\").replace("None", "").replace("\r\n","")
				if value == "":
					continue
				else:
					data1 += '"%s":"%s",' % (field, value)
			data1 += "}"
			data1 = data1.replace(",}", "}")
			event = Event()
			event.stanza = input_name
			event.data = data1
			ew.write_event(event)
			
		#Delta
		state = now_dt.strftime("%d/%m/%Y %H:%M:%S")
		helper.save_check_point(input_name, state)
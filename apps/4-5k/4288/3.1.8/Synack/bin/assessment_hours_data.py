import requests
import json
import os
import splunk_secrets_helper
import utils

filename = 'assessment_hours_id_list.txt'
filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'bin', 'index_lists', filename)
list_data = []
list_data = utils.read_file_to_list(filepath)
api_filename = 'api.conf'
api_filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'local', api_filename)

api_key = splunk_secrets_helper.fetch_synack_api_token()
base_url = utils.get_base_url(api_filepath)

# Set Headers
headers = { "Authorization": "Bearer " + api_key}

# Set Assessment URLs
assessment_url =  base_url + '/v1/assessments'


# Set page number for pagination
r = requests.get(assessment_url, headers=headers)
try:
  a_headers = r.headers
  a_page_results = a_headers['x-pagination']
  a_total_pages =json.loads(a_page_results)
  a_page_count = a_total_pages['total_pages'] + 1
except:
  a_page_count = 2

# Set assessment array
assess_id_array = []

for page_number in range(1,a_page_count):
  params = { "page[number]": page_number}
  a_r = requests.get(assessment_url, headers=headers, params=params)
  a_data = a_r.json() # parse JSON payload
  for a_obj in a_data:
    assess_id = a_obj['id']
    assess_id_array.append(assess_id)

for a_id in assess_id_array:
  # Set Assessment Hours URLs
  assessment_hours_url = base_url + '/v1/assessments/'+a_id+'/testing_hours'
  a_hours = requests.get(assessment_hours_url, headers=headers)
  hours_data = a_hours.json()
  assess_hours = hours_data['stats_total']
  if a_id not in list_data:
    row = json.dumps({
      "Assessment ID": a_id,
      "Assessment Hours": str(assess_hours)
    })
    print(row)
    list_data.append(a_id)

utils.update_file_with_list(filepath, list_data)

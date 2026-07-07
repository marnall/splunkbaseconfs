import requests
import json
import os
import splunk_secrets_helper
import utils

filename = 'pv_id_list.txt'
filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'bin', 'index_lists', filename)
list_data = []
list_data = utils.read_file_to_list(filepath)
api_filename = 'api.conf'
api_filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'local', api_filename)

api_key = splunk_secrets_helper.fetch_synack_api_token()
base_url = utils.get_base_url(api_filepath)

# Set Headers
headers = { "Authorization": "Bearer " + api_key}

# Set URLs
vuln_url = base_url + '/v1/vulnerabilities'

# Set page number for pagination
r = requests.get(vuln_url, headers=headers)
try:
  v_headers = r.headers
  v_page_results = v_headers['x-pagination']
  v_total_pages =json.loads(v_page_results)
  v_page_count = v_total_pages['total_pages'] + 1
except:
  v_page_count = 2

# Set vuln array
vuln_id_array = []

for page_number in range(1,v_page_count):
  params = { "page[number]": page_number}
  v_r = requests.get(vuln_url, headers=headers, params=params)
  v_data = v_r.json() # parse JSON payload
  for v_obj in v_data:
    vuln = v_obj['id']
    vuln_id_array.append(vuln)

for v_id in vuln_id_array:
  if v_id not in list_data:
    pv_url = base_url + '/v1/vulnerabilities/'+v_id+'/patch_verifications'
    pv_r = requests.get(pv_url, headers=headers)
    pv_data = pv_r.json()
    for pv_obj in pv_data:
      status = pv_obj['status']['status_text']
      status_time = pv_obj['status']['status_time']
      pv_row = json.dumps({
        "Vuln ID": v_id,
        "Status": status,
        "Status Time": status_time
      })
      print(pv_row)
    list_data.append(v_id)

utils.update_file_with_list(filepath, list_data)

import requests
import json
import os
import utils
import splunk_secrets_helper

filename = 'assessment_id_list.txt'
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
assessment_url = base_url + '/v1/assessments'
assessment_tags_url = base_url + '/v1/assessment_tags'

# Build a mapping of tag ID -> tag name
tag_id_to_name = {}
tags_r = requests.get(assessment_tags_url, headers=headers)
if tags_r.status_code == 200:
  for tag_obj in tags_r.json():
    tag_id_to_name[str(tag_obj['id'])] = tag_obj['name']

# Set page number for pagination
r = requests.get(assessment_url, headers=headers)
try:
  a_headers = r.headers
  a_page_results = a_headers['x-pagination']
  a_total_pages =json.loads(a_page_results)
  a_page_count = a_total_pages['total_pages'] + 1
except:
  a_page_count = 2


for page_number in range(1,a_page_count):
  params = { "page[number]": page_number}
  a_r = requests.get(assessment_url, headers=headers, params=params)
  a_data = a_r.json() # parse JSON payload
  for a_obj in a_data:
    assess_id = a_obj['id']
    if assess_id not in list_data:
      assess_id = a_obj['id']
      assess_name = a_obj['name']
      assess_codename = a_obj['codename']
      assess_category = a_obj['category']
      assess_tags = a_obj['tag_ids']
      a_tag_names = ', '.join(tag_id_to_name.get(str(t), str(t)) for t in assess_tags)
      row = json.dumps({
        "Assessment ID": assess_id,
        "Assessment Name": assess_name,
        "Assessment Codename": assess_codename,
        "Assessment Category": assess_category,
        "Assessment Tags": a_tag_names
      })
      print(row)
      list_data.append(assess_id)

utils.update_file_with_list(filepath, list_data)

import requests
import json
import os
import csv
import splunk_secrets_helper
import utils

filename = 'vuln_id_list.txt'
filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'bin', 'index_lists', filename)
api_filename = 'api.conf'
api_filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'local', api_filename)
csv_filename = 'vuln_status.csv'
csv_filepath = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'Synack', 'lookups', csv_filename)
list_data = []
list_data = utils.read_file_to_list(filepath)

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

with open(csv_filepath, "w") as csvfile:
   writer = csv.writer(csvfile, delimiter=",")
   writer.writerow(["Vuln ID", "Vuln Status"])
   for page_number in range(1, v_page_count):
    params = {"page[number]": page_number,"filter[include_attachments]": 0}
    v_r = requests.get(vuln_url, headers=headers, params=params)
    v_data = v_r.json() # parse JSON payload
    for v_obj in v_data:
      vuln = v_obj['id']
      if vuln not in list_data:
        v_timestamp = v_obj['resolved_at']
        title = v_obj['title']
        assessment = v_obj['listing']['codename']
        category = v_obj['category']['parent']
        subcategory = v_obj['category']['display']
        score = float(v_obj['cvss_final'])
        severity = utils.get_severity_level(score)
        # Extract the tag list
        tag_list = v_obj.get("tag_list", [])
        link = v_obj['link']
        # Extract tag names and concatenate them with commas
        tag_names = ", ".join(tag.get("name", "") for tag in tag_list)
        vuln_status = v_obj['vulnerability_status']['text']
        closed_at = v_obj.get('closed_at') or ''
        updated_at = v_obj.get('updated_at') or ''
        base_row = {
          "Vuln Date": v_timestamp,
          "Vuln ID": vuln,
          "Vuln Title": title,
          "Assessment": assessment,
          "Category": category,
          "Subcategory": subcategory,
          "CVSS Score": str(score),
          "Severity": severity,
          "Vuln Tags": tag_names,
          "Vuln Status": vuln_status,
          "Closed At": closed_at,
          "Updated At": updated_at,
          "Link": link
        }
        for e_obj in v_obj['exploitable_locations']:
          if 'type' in e_obj:
            asset_type = e_obj['type']
            row_data = dict(base_row)
            row_data["Asset Type"] = asset_type
            if asset_type == 'url':
              row_data["Vuln Location"] = e_obj['value']
            elif asset_type == 'other':
              row_data["Vuln Location"] = e_obj['value']
            elif asset_type == 'ip':
              row_data["Vuln Location"] = e_obj['address']
              row_data["Vuln Port"] = str(e_obj['port'])
            print(json.dumps(row_data))
        list_data.append(vuln)
      status = v_obj['vulnerability_status']['text']
      writer.writerow([vuln, status])
utils.update_file_with_list(filepath, list_data)

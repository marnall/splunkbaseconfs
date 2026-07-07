import requests
import json
import os
import splunk_secrets_helper
import utils

filename = 'sv_id_list.txt'
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
sus_vuln_url =  base_url + '/v1/suspected_vulnerabilities'

# Set page number for pagination
r = requests.get(sus_vuln_url, headers=headers)
try:
  sv_headers = r.headers
  sv_page_results = sv_headers['x-pagination']
  sv_total_pages =json.loads(sv_page_results)
  sv_page_count = sv_total_pages['total_pages'] + 1
except:
  sv_page_count = 2

for page_number in range(1,sv_page_count):
  params = { "page[number]": page_number}
  sv_r = requests.get(sus_vuln_url, headers=headers, params=params)
  sv_data = sv_r.json() # parse JSON payload
  for sv_obj in sv_data:
    sus_vuln = sv_obj['id']
    if str(sus_vuln) not in list_data:
      sv_timestamp = sv_obj['discovered_date']
      title = sv_obj['title']
      try:
        score = float(sv_obj['payload']['cvss_base'])
      except (TypeError, ValueError, KeyError):
        score = None
      severity = sv_obj['payload']['severity']
      confidence = sv_obj['payload']['confidence']
      sv_last_detected = sv_obj['last_detected_at']
      sv_status = sv_obj['status']
      cwe_ids = sv_obj['cwe_ids']
      cwes = ' '.join(str(x) for x in cwe_ids)
      cve_ids = sv_obj['cve_ids']
      cves = ' '.join(str(x) for x in cve_ids)
      for el_obj in sv_obj['exploitable_locations']:
        exp_type = el_obj['type']
        exp_loc = el_obj['value']
        exp_domain = el_obj.get('domain', '')
        exp_path = el_obj.get('path', '')
        row = json.dumps({
          "Sus Vuln Date": sv_timestamp,
          "Vuln ID": str(sus_vuln),
          "Vuln Title": title,
          "CVSS Score": str(score) if score is not None else '',
          "Severity": severity,
          "Confidence": confidence,
          "SV Last Detected": sv_last_detected,
          "SV Status": sv_status,
          "CWEs": cwes,
          "CVEs": cves,
          "Asset Type": exp_type,
          "SV Location": exp_loc,
          "SV Domain": exp_domain,
          "SV Path": exp_path
        })
        print(row)
      list_data.append(str(sus_vuln))

utils.update_file_with_list(filepath, list_data)

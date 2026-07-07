#!/usr/bin/python

import json
import logging
import requests
import sys
import os
import argparse
import time

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
    )

filepath = os.path.dirname(os.path.realpath(__file__))

# Setup argument parser
parser = argparse.ArgumentParser()

# Add long and short argument for CSP Token
parser.add_argument("--token", "-t", help="Optional argument to set the CSP Token used to call the VSS APIs")

# CSP APIs
def get_access(vsstoken):
    csp_info = requests.post('https://console.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize', data={'refresh_token': vsstoken})
    json_data = json.loads(csp_info.content.decode("utf-8"))
    if json_data['access_token']:
        logging.info("Access granted")
    return json_data['access_token']

# VSS APIs
def post_vss_query(headers, data):
    logging.info("Headers: {}".format(headers))
    logging.info("Data: {}".format(data))
    rdata = json.dumps(data)
    response = requests.post('https://api.securestate.vmware.com/v2/findings/query', headers=headers, data=rdata)    
    parsed = json.loads(response.content.decode("utf-8"))
    return parsed

def get_rules(headers):
    response = requests.get('https://api.securestate.vmware.com/v1/rules', headers=headers)
    parsed = json.loads(response.content.decode("utf-8"))
    return parsed['results']
    
def get_compliance_frameworks(headers) :
	response = requests.get('https://api.securestate.vmware.com/v1/compliance-frameworks', headers=headers)
	parsed = json.loads(response.content.decode("utf-8"))
	return parsed['results']

def get_compliance_controls(headers) :
    frameworks = get_compliance_frameworks(headers)
    data = []
    for framework in frameworks:
        response = requests.get('https://api.securestate.vmware.com/v1/compliance-frameworks/' + framework['id'] + '/controls', headers=headers)
        parsed = json.loads(response.content.decode("utf-8"))
        data += parsed['results']
    return data

def get_all_findings(headers, limit):
    request_data = generate_query_data()
    content, continuationToken = get_vss_query_api(headers, request_data)
    data = content
    nextToken = continuationToken

    while nextToken != "null" and len(data) < limit:
        time.sleep(0.5)
        logging.info("Gathered result count: {}".format(len(data)))
        request_data['paginationInfo']['continuationToken'] = nextToken
        results, cToken = get_vss_query_api(headers, request_data)
        nextToken = cToken
        data += results
    return data

# Helper Methods
def get_vss_query_api(headers, request_data):
    logging.info("Entering get_vss_query_api")
    content = post_vss_query(headers, request_data)
    
    if 'continuationToken' in content and 'results' in content:
        return content['results'], content['continuationToken']
    elif 'results' in content and 'continuationToken' not in content:
        return content['results'], 'null'
    else:
        logging.info("Logging content due to error: {}".format(content))
        return [], 'null'

def generate_query_data(severity = None, continuationToken = None):
    request_data = {
        "filters": {},
        "paginationInfo": {"continuationToken": None, "pageSize": 1000},
        }

    if severity:
        request_data['filters']['levels'].append(severity)
    if continuationToken:
        request_data['paginationInfo']['continuationToken'] = continuationToken

    return request_data

def write_file_json(filename, data):
    with open(filename, 'w+') as rules_file:
        json.dump(data, rules_file, indent=4, sort_keys=True)

def get_token():
    with open(filepath + "/csp-token.txt", 'r') as csp_token_file:
        first_line = csp_token_file.readline()
        token = first_line.split(":")[1].strip()
        return token

def main():
    # read arguments from the command line
    args = parser.parse_args()

    # check for --token
    if args.token:
        print("Using the command line provided CSP Token")
        vsstoken = args.token

    else:
        vsstoken = get_token()
    
    access_token = get_access(vsstoken)
    headers = {'Authorization': 'Bearer {}'.format(access_token)}
    
    # GET Rules
    data = get_rules(headers)
    filename = filepath + "/data/vss_rules.json"
    write_file_json(filename=filename, data=data)
    
  	# GET Compliance
    data = get_compliance_frameworks(headers)
    filename = filepath + "/data/vss_compliance_frameworks.json"
    write_file_json(filename=filename, data=data)

  	# GET Compliance_Controls
    data = get_compliance_controls(headers)
    filename = filepath + "/data/vss_compliance_controls.json"
    write_file_json(filename=filename, data=data)

    # GET Findings
    # request_data = generate_query_data()
    # content = post_vss_query(headers, request_data)
    # data = content['results']
    
    # # GET All Findings
    findings_limit = 100000
    data = get_all_findings(headers, findings_limit)

    filename = filepath + "/data/vss_findings.json".format()
    write_file_json(filename=filename, data=data)

if __name__ == '__main__':
    main()


# encoding = utf-8

import json
import requests
import time
import uuid
from requests.auth import HTTPBasicAuth
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # company_guid = definition.parameters.get('company_guid', None)
    # impacts_risk_vector_grade = definition.parameters.get('impacts_risk_vector_grade', None)
    # severity_category = definition.parameters.get('severity_category', None)
    # api_token = definition.parameters.get('api_token', None)
    # api_url = definition.parameters.get('api_url', None)
    pass

def get_companies(helper, token, filter_company):
    
    api_url = f'https://api.bitsighttech.com/v1/companies'
    
    helper.log_info(f'Querying BitSight Companies API now...')
    helper.log_info(f'GET {api_url}')
    
    response = requests.get(api_url, auth=HTTPBasicAuth(token, ""))
    
    all_companies = []
    filtered_companies = []
    retry_count = 0
    
    if response.status_code == 200:
    
        data = response.json()
        
        all_companies.extend(data.get("companies", []))
    else:
        helper.log_error(f"Failed to retrieve Companies data. Status code: {response.status_code}")
        filtered_companies = None    
    
    if filter_company == "*":
        filtered_companies = all_companies
    else:
        if company_exists(all_companies, filter_company):
            
            filtered_company = next((c for c in all_companies if c["guid"] == filter_company), None)
            filtered_companies.append(filtered_company)
    
    return filtered_companies

def company_exists(companies, search_val):
    for c in companies:
        if c.get('guid') == search_val:
            return True
    return False

def get_findings(helper, init_url, company_guid, token, irvd, sevcat, fsamp):
    init_url = init_url.rstrip('/')
    api_url = f'{init_url}/ratings/v1/companies/{company_guid}/findings'
    api_url = api_url + f'?impacts_risk_vector_details={irvd}'
    api_url = api_url + f'&severity_category={sevcat}'
    
    helper.log_info(f'hello world {fsamp}')
    
    if fsamp==-1:
        api_url = api_url
    elif fsamp==1:
        api_url = api_url + f'&unsampled=true'
    else:
        api_url = api_url + f'&unsampled=false'
    
    helper.log_info(f'Querying BitSight Findings API now. company={company_guid} | irvd={irvd} | sevparam={sevcat}')
    helper.log_info(f'GET {api_url}')
    
    all_results = []
    
    url = api_url
    
    page = 1
    max_retries = 10
    retry_count = 0

    while url and retry_count < max_retries:
        # Make the GET request with basic authentication
        response = requests.get(url, auth=HTTPBasicAuth(token, ""))
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            
            # Collect the results
            all_results.extend(data.get("results", []))
            
            # Get the next URL from the links
            url = data.get("links", {}).get("next")
            
            retry_count = 0
        elif response.status_code > 499:
            retry_count += 1
            if retry_count < max_retries:
                # Sleep for 10 seconds and then retry the request
                helper.log_warning(f"API query failed due to 5xx error (BitSight Server was unresponsive). Will retry for a maximum of 10x. {response.status_code}")
                time.sleep(10)
            else:
                helper.log_error(f"Failed after {max_retries} retries. Status code: {response.status_code}")
                break
        else:
            helper.log_error(f"Failed to Findings retrieve data. Status code: {response.status_code}")
            break
    
        page = page + 1
    
    helper.log_info(f'API ran {str(page)} times due to pagination.')
    
    return all_results

def collect_events(helper, ew):
    
    stanzaname = helper.get_input_stanza_names()
    init_company_guid = helper.get_arg('company_guid')
    opt_impacts_risk_vector_grade = helper.get_arg('impacts_risk_vector_grade')
    opt_findings_sampling = int(helper.get_arg('findings_sampling'))
    opt_api_token = helper.get_arg('api_token')
    opt_api_url = helper.get_arg('api_url')

    sev_param = ','.join(helper.get_arg('finding_severity'))
    _splunkSkedInputId = str(uuid.uuid4())
    
    helper.log_info(f'Start of collection. stanza={stanzaname}')
    helper.log_info(f'This sked-collection\'s interval ID is {_splunkSkedInputId}')
    
    if init_company_guid == "*":
        company_guid = "all"
        helper.log_info(f'Collection method is set to retrieve all companies allowed for the token provided.')
    else:
        company_guid = init_company_guid
        helper.log_info(f'Collection method is set to retrieve data from one specific company.')
    
    companies = get_companies(helper, opt_api_token, init_company_guid)
    
    if companies is None or len(companies)==0:
        helper.log_info(f'The BitSight API was successful but did not return any Company or guid="{company_guid}". This input/collection ends here.')
        return
    
    meta_source = f'bitsight_companies://{stanzaname}'
    helper.log_info(f'Writing Companies meta...')
    
    ev = 0
    
    for c in companies:
        c['_splunkSkedInputId'] = _splunkSkedInputId
        # Indexing Companies as separate sourcetype first
        data = json.dumps(c, separators=(',', ':'))
        event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype='bitsight:companies', data=data)
        ew.write_event(event)
        ev = ev + 1
        
        # Now querying the API for each company
        
        companyDetails = {
            "guid": c['guid'],
            "name": c['name'],
            "shortname": c['shortname'],
            "rating": c['rating'],
            "rating_date": c['rating_date'],
        }
        
        company_guid_api = companyDetails['guid']
        
        findings = get_findings(helper, opt_api_url, company_guid_api, opt_api_token, opt_impacts_risk_vector_grade, sev_param, opt_findings_sampling)
        
        if findings is None or len(findings)==0:
            helper.log_info('The BitSight API was successful but did not return any findings for company_guid="{company_guid_api}". Onto the next company...')
            continue
        
        helper.log_info(f'A total of {len(findings)} findings retrieved for company {company_guid_api}. Writing findings events...')
        
        meta_source = f'bitsight_findings://{stanzaname}'
        
        for f in findings:
            
            f['companyDetails'] = companyDetails
            f['_splunkSkedInputId'] = _splunkSkedInputId
            
            data = json.dumps(f, separators=(',', ':'))
            
            event = helper.new_event(source=meta_source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
            ew.write_event(event)
            ev = ev + 1
    
    helper.log_info(f'Total events: {ev}')
    helper.log_info(f'Collection ends here. Reaching this part means a successful collection.')
    
    
    
    
    
    
import abuseIPDB_connector
from abuseIPDB_control_helpers import get_messages, surface_error_message_no_trace
from abuseIPDB_exception import AbuseIPDB_Exception

def make_check_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_check_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'check')

def make_checkblock_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_checkblock_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'checkblock')

def make_reports_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_reports_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'reports')

def make_report_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_report_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'report')

def make_blacklist_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_blacklist_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'blacklist')

def make_account_request_in_search_event(splunk_service, record, params):
  response = abuseIPDB_connector.make_account_request(splunk_service, params)
  return handle_search_event_response(splunk_service, record, params, response, 'account')

def handle_search_event_response(splunk_service, record, params, response, endpoint):
  status_code = response.status_code
  body = response.json()

  if status_code == 200:
    data = body['data']

    if endpoint == 'reports':
        reports = []
        if status_code == 200:
          for result in body['data']['results']:
            result_parsed = {}
            result_parsed['ipAddress'] = params['ipAddress']
            result_parsed.update(result)
            categories_parsed = []
            for category in result['categories']:
              categories_parsed.append(category)
            result_parsed['categories'] = categories_parsed
            reports.append(result_parsed) 
          return reports
    
    elif endpoint == 'blacklist':
      blacklist = []
      if status_code == 200:
        for result in body['data']:
          result_parsed = {}
          result_parsed['ipAddress'] = result['ipAddress']
          result_parsed['abuseConfidenceScore'] = result['abuseConfidenceScore']
          result_parsed['countryCode'] = result['countryCode']
          result_parsed['lastReportedAt'] = result['lastReportedAt']
          blacklist.append(result_parsed)
        return blacklist
    
    else:
      for datum in data:
        record[datum] = data[datum]
      return record
    
  elif status_code >= 400:
    if endpoint == "report" and body['errors'] and body['errors'][0]['status'] == 403:
      pass
    elif (status_code == 429):
      surface_error_message_no_trace(get_messages(splunk_service), "Daily limit exceeded for " + endpoint + " endpoint. Wait until tomorrow or upgrade to increase your limit.")
    if 'errors' in body:
      raise AbuseIPDB_Exception("Error " + str(status_code) + ": " + body['errors'][0]['detail'])
    else:
      raise AbuseIPDB_Exception("Error " + str(status_code))

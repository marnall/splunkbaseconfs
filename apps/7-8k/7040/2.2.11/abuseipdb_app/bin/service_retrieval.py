import splunklib.client as client
from abuseIPDB_exception import AbuseIPDB_Exception

# retrieve password from Splunk's storage/passwords endpoint
def get_api_key(service):
  if storage_password_exists(service) == False:
    raise AbuseIPDB_Exception("AbuseIPDB App: API key not yet configured or list_all_passwords permission missing. Go to the App to setup.")

  service.namespace = client.namespace(app="abuseipdb_app", sharing="app")  # make sure this is set so we don't get all passwords...
  api_key = service.storage_passwords["abuseipdb_api_key:admin:"]

  if api_key is None:
    raise AbuseIPDB_Exception("AbuseIPDB App: API key not yet configured or list_all_passwords permission missing. Go to the App to setup.")
  else:
    return api_key.clear_password

# check if api key is set for the app
def storage_password_exists(service):
  service.namespace = client.namespace(app="abuseipdb_app", sharing="app")
  try:
    return service.storage_passwords["abuseipdb_api_key:admin"] is not None
  except Exception as e:
    return False

def get_proxy_settings(service):
  service.namespace = client.namespace(app="abuseipdb_app", sharing="app")
  control_coll = service.kvstore['abuseipdb_control_coll']
  config_dict = {}
  try:
    kvstore_json = control_coll.data.query()
    for kvpair in kvstore_json:
      config_dict[kvpair['_key']] = kvpair['value']
  except Exception as e:
    return None

  if config_dict['proxyEnabled'] == "1" and config_dict['proxyAuth'] == "1":
    return {
      'http' : str(config_dict['proxyProtocol']).lower() + "://" + config_dict['proxyUsername'] + ":" + config_dict['proxyPassword'] + "@" + config_dict['proxyHost'] + ":" + config_dict['proxyPort'],
      'https' : str(config_dict['proxyProtocol']).lower() + "://" + config_dict['proxyUsername'] + ":" + config_dict['proxyPassword'] + "@" + config_dict['proxyHost'] + ":" + config_dict['proxyPort']
    }
  elif config_dict['proxyEnabled'] == "1":
    return {
      'http' : str(config_dict['proxyProtocol']).lower() + "://" + config_dict['proxyHost'] + ":" + config_dict['proxyPort'],
      'https' : str(config_dict['proxyProtocol']).lower() + "://" + config_dict['proxyHost'] + ":" + config_dict['proxyPort']
    }
  else:
    return None

#-----------------------------------------------------------------
# the functions below are useful in instances where the Splunk service is not directly available, but can be retrieved with different methods

# retrieve password from Splunk's storage/passwords endpoint for the report functionality
def get_api_key_with_session_key(session_key):
  service = get_service_with_session_key(session_key)
  return get_api_key(service)

#retrieve api key from storage with a Splunk token
def get_api_key_with_token(token):
  service = get_service_with_token(token)
  return get_api_key(service)

#retrieve splunk service instance with a session key
def get_service_with_session_key(session_key):
  service = client.connect(
    host = "localhost",
    port = 8089,
    token = session_key
  )
  return service

#retrieve splunk service instance with token
def get_service_with_token(token):
  service = client.connect(
    host = "localhost",
    port = 8089,
    splunkToken = token
  )
  return service

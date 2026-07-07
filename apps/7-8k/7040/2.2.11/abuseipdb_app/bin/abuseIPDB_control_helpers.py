from abuseIPDB_connector import make_blacklist_request, make_account_request
from abuseIPDB_exception import AbuseIPDB_Exception
from splunklib.client import namespace
from datetime import datetime, timedelta

FAST_UPDATE_INTERVAL = 3600
SLOW_UPDATE_INTERVAL = 21600
SLOWEST_UPDATE_INTERVAL = 86400

# Returns whether or not the day has rolled over
def has_day_rolled_over(current_time, account_last_checked_at):
  return account_last_checked_at != "never" and \
      current_time.date() != datetime.strptime(account_last_checked_at, '%Y-%m-%d %H:%M:%S.%f').date()

# Returns whether the blacklist is over n days old
def is_blacklist_over_n_days_old(current_time, blacklist_last_updated_at, n):
  return blacklist_last_updated_at != "never" and \
      (current_time - datetime.strptime(blacklist_last_updated_at, '%Y-%m-%d %H:%M:%S.%f')) > timedelta(days=n)

# Returns whether the subscription is churning
def is_subscription_churning(trial_days_left, cycle_days_left):
  return trial_days_left is not None and \
      cycle_days_left is not None and \
      trial_days_left == cycle_days_left and \
      trial_days_left < timedelta(days=3)

# Returns whether the subscription is ending
def is_subscription_ending(cycle_days_left):
  return cycle_days_left is not None and \
      cycle_days_left < timedelta(days=3)

# Returns whether the blacklist should be updated
def should_blacklist_be_updated(blacklist_is_updating, force_blacklist_update, blacklist_auto_update, blacklist_last_updated_at, blacklist_auto_update_interval, current_time):
  if blacklist_is_updating == "1":
    return False

  if force_blacklist_update == "1":
    return True
  
  elif blacklist_auto_update == "1":
    if blacklist_last_updated_at == "never":
      return True
    
    blacklist_age = current_time - datetime.strptime(blacklist_last_updated_at, '%Y-%m-%d %H:%M:%S.%f')
    if blacklist_age > timedelta(seconds=int(blacklist_auto_update_interval)):
      return True

  else:
    return False

# Returns whether the control script should run
def should_control_script_run(account_last_checked_at, force_blacklist_update, current_time):
  if account_last_checked_at == "never" or force_blacklist_update == "1":
    return True
  
  else:
    time_since_last_check = current_time - datetime.strptime(account_last_checked_at, '%Y-%m-%d %H:%M:%S.%f')
    if time_since_last_check > timedelta(seconds=FAST_UPDATE_INTERVAL - 5):
      return True

    else:
      return False

# Updates a single key-value pair in the KV store
def update_kvstore_pair(control_coll, pair_dict):
  update_array = []
  for key, value in pair_dict.items():
    update_array.append({ "_key": key, "value": str(value) })
  control_coll.data.batch_save(*update_array)

# Updates all key-value pairs in the KV store
def update_all_kvstore_pairs(control_coll, config_dict):
  update_array = []
  for key, value in config_dict.items():
    update_array.append({ "_key": key, "value": str(value) })
  control_coll.data.batch_save(*update_array)

# Retrieves a single key-value pair from the KV store
def get_kvstore_value(control_coll, key):
  return control_coll.data.query_by_id(key)['value']

# Retrieves all key-value pairs from the KV store
def get_all_kvstore_values(control_coll):
  return control_coll.data.query()

# Retrieves all key-value pairs from the KV store as a dictionary object
def get_all_kvstore_values_as_dict(control_coll):
  kvstore_json = get_all_kvstore_values(control_coll)
  config_dict = {}
  for kvpair in kvstore_json:
      config_dict[kvpair['_key']] = kvpair['value']
  return config_dict

def set_default_kvstore_values(control_coll, config_dict):
  default_settings = {
    "minimumAbuseConfidenceScore": "100", # used for the automated blacklist endpoint
    "blacklistLastUpdatedAt": "never",  # how we know if the blacklist is stale
    "blacklistAutoUpdate": "0", # whether the blacklist should be updated automatically (0 or 1)
    "blacklistAutoUpdateInterval": "86400", # how often (in seconds) to update the blacklist
    "accountLevel": "Individual", # corresponds to the user's highest "tier" (role) in abuseIPDB
    "blacklistSize": "0", # size of the currently loaded blacklist (caps at 10k for individual, 100k for basic, 500k for premium)
    "accountLastCheckedAt": "never",  # used for some control script logic
    "isSubscribed": "0",  # if the user is subscribed (e.g. paying)
    "forceBlacklistUpdate": "0",  # if the blacklist should be updated immediately
    "blacklistIsUpdating": "0", # wether the blacklist is currently updating or not
    "appVersion": "2.2.11",  # the version of the app
    "isTrial": "0",  # if the user is on a trial subscription (isSubscribed will also be 1)
    "hasSeenOptionsPage": "0",  # if the user has seen the options page
    "proxyEnabled": "0",  # if the user has enabled the proxy
    "proxyProtocol": "",  # the proxy protocol
    "proxyHost": "",  # the proxy host
    "proxyPort": "",  # the proxy port
    "proxyAuth": "0", # if the proxy requires authentication
    "proxyUsername": "",  # the proxy username
    "proxyPassword": "",  # the proxy password
  }

  missing = {}

  for key, value in default_settings.items():
    if key not in config_dict:
      missing[key] = value
  
  missing["appVersion"] = "2.2.11"
  update_all_kvstore_pairs(control_coll, missing)
  return get_all_kvstore_values_as_dict(control_coll)

# Retrieves the account information from the AbuseIPDB API
def get_abuse_account_info(service):
  response = make_account_request(service, {})
  if response.status_code == 401:
    raise AbuseIPDB_Exception('Invalid API key. Please set your API key in the AbuseIPDB app settings.')
  elif response.status_code != 200:
    raise AbuseIPDB_Exception('Failed to retrieve account information from AbuseIPDB.')
  return response.json()['data']

# Surface an error message
def surface_error_message(messages, exception):
  messages.create(name="AbuseIPDB App Error", value="AbuseIPDB App: Error. " + str(exception) + " -- Trace written to error log. You can report this error to us at splunk@abuseipdb.com", severity="error")

def surface_error_message_no_trace(messages, exception):
  messages.create(name="AbuseIPDB App Error", value="AbuseIPDB App: Error. " + str(exception), severity="error")

def get_messages(service):
  service.namespace = namespace(app="abuseipdb_app", sharing="app")
  return service.messages

# Validate config values
def validate_config_values(config_dict):
  if config_dict['blacklistAutoUpdate'] not in ["0", "1"]:
    raise AbuseIPDB_Exception('Invalid value for blacklistAutoUpdate. Must be 0 or 1.')
  if int(config_dict['minimumAbuseConfidenceScore']) < 25 or int(config_dict['minimumAbuseConfidenceScore']) > 100:
    raise AbuseIPDB_Exception('Invalid value for minimumAbuseConfidenceScore. Must be between 25 and 100, inclusive.')
  if config_dict['blacklistAutoUpdateInterval'] not in [str(FAST_UPDATE_INTERVAL), str(SLOW_UPDATE_INTERVAL), str(SLOWEST_UPDATE_INTERVAL)]:
    raise AbuseIPDB_Exception('Invalid value for blacklistAutoUpdateInterval. Must be 3600, 21600, or 86400.')

# Returns the size of the blacklist
def get_blacklist_size(blacklist_coll):
  blacklist_size = 0
  while True:
    blacklist_size_step = len(blacklist_coll.data.query(skip=blacklist_size))
    if blacklist_size_step == 0:
      break
    blacklist_size += blacklist_size_step
  return blacklist_size

# Deletes the blacklist
def delete_blacklist(blacklist_coll):
  blacklist_coll.data.delete()

# Updates the blacklist in the KV store
def update_blacklist_and_return_ips_written(service, messages, params, blacklist_coll, current_time):
  current_time_str = str(current_time)
  response = make_blacklist_request(service, params)
  if response.status_code == 429:
    surface_error_message_no_trace(messages, 'AbuseIPDB Blacklist API quota exceeded. Wait until tomorrow or upgrade to increase your limit.')
    return -1
  elif response.status_code != 200:
    surface_error_message_no_trace(messages, 'Failed to retrieve blacklist from AbuseIPDB.')
    return -1
  body = response.json()
  batch = []

  for ip_info in body['data']:
    ip_info['updatedAt'] = current_time_str # Flag for deletion of old, unupdated entries
    ip_info['_key'] = ip_info['ipAddress']  # To find out which ones to update
    ip_info['ip'] = ip_info['ipAddress']
    del ip_info['ipAddress']
    batch.append(ip_info)
    
    # Max batch size is 1,000 in Splunk 9.3 onwards
    if len(batch) == 1000:
      blacklist_coll.data.batch_save(*batch) # Unpack into separate args
      batch = []

  # Add final batch
  if len(batch) > 0:
    blacklist_coll.data.batch_save(*batch)

  query_str = '''{"updatedAt":{"$ne":"''' + current_time_str + '''"}}'''
  blacklist_coll.data.delete(query=query_str)

  # Return the size of the blacklist
  size_of_blacklist = get_blacklist_size(blacklist_coll)
  return size_of_blacklist

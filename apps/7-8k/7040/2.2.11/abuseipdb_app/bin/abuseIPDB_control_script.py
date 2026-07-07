import sys
from datetime import datetime, timedelta, timezone
from time import sleep
from abuseIPDB_control_helpers import *
from service_retrieval import get_service_with_token
from splunklib.client import namespace
from abuseIPDB_exception import AbuseIPDB_Exception
from service_retrieval import storage_password_exists
import traceback

FAST_UPDATE_INTERVAL = 3600
SLOW_UPDATE_INTERVAL = 21600
SLOWEST_UPDATE_INTERVAL = 86400

def runScript(service, messages):

  #messages.create(name="AbuseIPDB App", value="AbuseIPDB App: Running control script...", severity="info")
  control_coll = service.kvstore['abuseipdb_control_coll']
  blacklist_coll = service.kvstore['abuseipdb_blacklist_coll']
  current_time = datetime.now()
  current_time_utc = datetime.now(timezone.utc)

  config_dict = {}
  try:
    config_dict = get_all_kvstore_values_as_dict(control_coll)  # Get app config values from KV store
  except Exception as e:
    return

  if len(config_dict) == 0:
    return
  
  # if the config is empty (possible error or when upgrading from an older app version without the kv store)
  if ('appVersion' in config_dict and config_dict['appVersion'] != "2.2.11"):
    # i.e. only do this if the API key is set, if not it's a first time setup and showing it wouldn't make sense
    if storage_password_exists(service):
      config_dict = set_default_kvstore_values(control_coll, config_dict)
    else:
      return

  # if account has been checked at least once and it hasn't been the fast update interval - 5 and force blacklist update is 0, return
  # if the account's never been checked we should check it here
  if not should_control_script_run(config_dict['accountLastCheckedAt'], config_dict['forceBlacklistUpdate'], current_time):
    return

  # we should only be reaching this point if we're forcing a blacklist update or it's been more than an hour since the last account check

  validate_config_values(config_dict) # Validate some of these values to ensure they're within acceptable ranges
  account_info = get_abuse_account_info(service)  # Get account info from AbuseIPDB API

  config_dict['accountLevel'] = account_info['tier']

  # parse these ahead of time for cleaner code
  if account_info['billingDetails']['trialEndsAt'] is not None:
    trial_days_left = datetime.strptime(account_info['billingDetails']['trialEndsAt'], '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=timezone.utc) - current_time_utc
  else:
    trial_days_left = None

  if account_info['billingDetails']['cycleEndsAt'] is not None:
    cycle_days_left = datetime.strptime(account_info['billingDetails']['cycleEndsAt'], '%Y-%m-%dT%H:%M:%S+00:00').replace(tzinfo=timezone.utc) - current_time_utc
  else:
    cycle_days_left = None

  # Reset the account lapsing warning flag if it's a new day
  if has_day_rolled_over(current_time, config_dict['accountLastCheckedAt']):
    # Surface warnings
    # Make these all once daily to avoid annoying the user
    if is_blacklist_over_n_days_old(current_time, config_dict['blacklistLastUpdatedAt'], 7):
      delete_blacklist(blacklist_coll)
      config_dict['blacklistLastUpdatedAt'] = "never"
      config_dict['blacklistSize'] = "0"
      messages.create(name="AbuseIPDB App Blacklist Wiped", value="AbuseIPDB App: Your blacklist is too stale and has been wiped. You can enable automatic updates or manually retrieve it again at any time.", severity="warn")
    elif is_blacklist_over_n_days_old(current_time, config_dict['blacklistLastUpdatedAt'], 3):
      messages.create(name="AbuseIPDB App Blacklist Out of Date", value="AbuseIPDB App: Your blacklist is becoming stale and will be deleted soon. Either enable automatic updating or manually wipe it from the Options page.", severity="warn")

    if account_info['isSubscribed']:
      if is_subscription_churning(trial_days_left, cycle_days_left):
        messages.create(name="AbuseIPDB App Trial Ending", value="AbuseIPDB App: Your trial subscription is ending soon. Consider upgrading to a paid subscription.", severity="warn")
      elif is_subscription_ending(cycle_days_left):
        messages.create(name="AbuseIPDB App Subscription Ending", value="AbuseIPDB App: Your subscription is ending soon. Consider renewing your subscription.", severity="warn")

  # warnings for lapsed
  if config_dict['isSubscribed'] == "1" and config_dict['isTrial'] == "1" and not account_info['isSubscribed']:
    messages.create(name="AbuseIPDB App Trial Ended", value="AbuseIPDB App: Your trial subscription has ended. Any premium features have been downgraded. If you found the AbuseIPDB app useful, consider subscribing.", severity="warn")
  elif config_dict['isSubscribed'] == "1" and config_dict['isTrial'] == "0" and not account_info['isSubscribed']:
    messages.create(name="AbuseIPDB App Subscription Ended", value="AbuseIPDB App: Your subscription has ended. Any premium features have been downgraded.", severity="warn")

  # set this here AFTER the previous checks so we can show the right message before we change the cached value
  config_dict['isSubscribed'] = "1" if account_info['isSubscribed'] else "0"
  if config_dict['isSubscribed'] == "1":
    config_dict['isTrial'] = "1" if account_info['billingDetails']['trialEndsAt'] is not None else "0"
  else:
    config_dict['isTrial'] = "0"

  force_set_abuse_score = False
  # Fallback to a safe value if we're not subscribed but the user has set a non-default value for minimumAbuseConfidenceScore
  if not account_info['isSubscribed'] and config_dict['minimumAbuseConfidenceScore'] != 100:
    config_dict['minimumAbuseConfidenceScore'] = "100"
    force_set_abuse_score = True

  force_set_update_interval = False
  # Fallback to a safe value if we're not subscribed but the user has set a non-default value for blacklistAutoUpdateInterval
  if not account_info['isSubscribed'] and config_dict['blacklistAutoUpdateInterval'] == str(FAST_UPDATE_INTERVAL):
    config_dict['blacklistAutoUpdateInterval'] = str(SLOWEST_UPDATE_INTERVAL)
    force_set_update_interval = True

  # Only update the blacklist if force is on (usually by clicking the manual refresh button)
  # or if auto update is on and enough time has passed since the last update
  if should_blacklist_be_updated(config_dict['blacklistIsUpdating'], config_dict['forceBlacklistUpdate'], config_dict['blacklistAutoUpdate'], config_dict['blacklistLastUpdatedAt'], config_dict['blacklistAutoUpdateInterval'], current_time):
    update_kvstore_pair(control_coll, {'blacklistIsUpdating' : '1'})
    config_dict['blacklistIsUpdating'] = "1"
    params = {}
    params["limit"] = account_info['endpoints']['blacklist']['additionalInfo']['fetchLimit']
    params['confidenceMinimum'] = config_dict['minimumAbuseConfidenceScore']
    #messages.create(name="AbuseIPDB App Blacklist Update", value="AbuseIPDB App: Updating blacklist...", severity="info")
    ips_written = update_blacklist_and_return_ips_written(service, messages, params, blacklist_coll, current_time)
    if ips_written != -1:
      config_dict['blacklistLastUpdatedAt'] = str(current_time)
      config_dict['blacklistSize'] = str(ips_written)
    update_kvstore_pair(control_coll, {'blacklistIsUpdating' : '0'})
    config_dict['blacklistIsUpdating'] = "0"
    update_kvstore_pair(control_coll, {'forceBlacklistUpdate' : "0"})
    config_dict['forceBlacklistUpdate'] = "0"

  # Update the app config KV store with any changed values
  # but don't overwrite the abuse score or update interval if they've been changed here
  config_dict_new = get_all_kvstore_values_as_dict(control_coll)  # Get app config values from KV store in case they've changed
  if not force_set_abuse_score and config_dict_new['minimumAbuseConfidenceScore'] != config_dict['minimumAbuseConfidenceScore']:
    config_dict['minimumAbuseConfidenceScore'] = config_dict_new['minimumAbuseConfidenceScore']
  if config_dict_new['blacklistAutoUpdate'] != config_dict['blacklistAutoUpdate']:
    config_dict['blacklistAutoUpdate'] = config_dict_new['blacklistAutoUpdate']
  if not force_set_update_interval and config_dict_new['blacklistAutoUpdateInterval'] != config_dict['blacklistAutoUpdateInterval']:
    config_dict['blacklistAutoUpdateInterval'] = config_dict_new['blacklistAutoUpdateInterval']
  
  config_dict['accountLastCheckedAt'] = str(current_time)
  update_all_kvstore_pairs(control_coll, config_dict)

# Provides access to this script using either Splunk's internal system or through our own scripts/elsewhere by passing in the service object
# Remember that this script is run every 30 seconds by the Splunk scheduler
def mainFunc(service = None):
  sleep(5)  # To prevent a race condition with the KV store app options
  if service is None:
    token = sys.stdin.readlines()[0]
    service = get_service_with_token(token)
    
  service.namespace = namespace(app="abuseipdb_app", sharing="app")
  messages = service.messages
  control_coll = service.kvstore['abuseipdb_control_coll']
  try:
    runScript(service, messages)
  except AbuseIPDB_Exception as e:
    surface_error_message_no_trace(messages, e)
    update_kvstore_pair(control_coll, {'blacklistIsUpdating' : '0'})
    update_kvstore_pair(control_coll, {'forceBlacklistUpdate' : "0"})
  except Exception as e:
    surface_error_message(messages, e)
    update_kvstore_pair(control_coll, {'blacklistIsUpdating' : '0'})
    update_kvstore_pair(control_coll, {'forceBlacklistUpdate' : "0"})
    sys.stderr.write("AbuseIDPB App error: " + traceback.format_exc().replace("\n", " -- ") + "\n")

if __name__ == "__main__":
  mainFunc()

# Functions to provide common utilities to other scripts

import base64
from datetime import datetime, timedelta
import traceback

LAST_EVENT_INGESTED_DATE_KEY = 'last_event_ingested_date'
SLEEP_UNTIL_KEY = 'sleep_until_date'

########## Base64 encodes the input string
def base64_encode(input: str):
    input_bytes = input.encode('ascii')
    base64_bytes = base64.b64encode(input_bytes)
    base64_message = base64_bytes.decode('ascii')
    return base64_message
########## -----------------------------------------------


########## Retrieves the start date value from the StoragePasswords
def get_start_date(helper, default_start_date: datetime):
    start_date_to_use = default_start_date
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
    stored_val = get_stored_val(helper, target_key, default_start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
    
    try:
        if (stored_val is not None) and (stored_val.clear_password != None) and (stored_val.clear_password != 'None') and (stored_val.clear_password != ''):
            # Take the value from the existing entry and convert it to a datetime
            start_date_to_use = datetime.strptime(stored_val.clear_password, '%Y-%m-%dT%H:%M:%S.%fZ')
    except Exception as e:
        helper.log_error(f'Retrieval of start date failed: {str(e)} - value will be cleared')
        traceback.print_exc()
        clear_start_date(helper)   
    return start_date_to_use
########## -----------------------------------------------


########## Saves the start date value in the StoragePasswords
def save_start_date(helper, new_value: datetime):
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
    stored_val = get_stored_val(helper, target_key, None)
    stored_val.update(password=new_value.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
########## -----------------------------------------------


########## Clears the start date value from the StoragePasswords
def clear_start_date(helper):
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
    helper.service.storage_passwords.delete(target_key)
########## -----------------------------------------------


########## Retrieves the sleep-until date value from the StoragePasswords
def get_sleep_until(helper):
    sleep_util_date = None
    target_key = f'{str(helper.get_input_stanza_names())}_{SLEEP_UNTIL_KEY}'
    stored_val = get_stored_val(helper, target_key, None)
    
    try:
        if (stored_val is not None) and (stored_val.clear_password != None) and (stored_val.clear_password != 'None') and (stored_val.clear_password != ''):
            # Take the value from the existing entry and convert it to a datetime
            sleep_util_date = datetime.strptime(stored_val.clear_password, '%Y-%m-%dT%H:%M:%S.%fZ')
    except Exception as e:
        helper.log_error(f'Retrieval of sleep-until failed: {str(e)} - value will be cleared')
        traceback.print_exc()
        clear_sleep_until(helper)   
    return sleep_util_date
########## -----------------------------------------------


########## Saves the sleep-until date value in the StoragePasswords
def save_sleep_until(helper, new_value: datetime):
    target_key = f'{str(helper.get_input_stanza_names())}_{SLEEP_UNTIL_KEY}'
    stored_val = get_stored_val(helper, target_key, None)
    stored_val.update(password=new_value.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
########## -----------------------------------------------


########## Removes the sleep-until date value from the StoragePasswords
def clear_sleep_until(helper):
    target_key = f'{str(helper.get_input_stanza_names())}_{SLEEP_UNTIL_KEY}'
    helper.service.storage_passwords.delete(target_key)
########## -----------------------------------------------


########## Returns a StoragePassword object with the specified key - a new one is created if it does not already exist
def get_stored_val(helper, target_key: str, default_value: str):
    stored_val = None
    
    try:
        # Check for an existing entry
        for entry in helper.service.storage_passwords.iter():
            if entry.name == f':{target_key}:':
                helper.log_debug(f'Found existing StoragePassword for {target_key}')
                stored_val = entry
                break
        # If no existing entry found, go ahead and create one using the default value
        if stored_val is None:
            helper.log_debug(f'Creating StoragePassword for {target_key}')
            stored_val = helper.service.storage_passwords.create(password=default_value, username=target_key)

    except Exception as e:
        helper.log_error(f'Retrieval of stored value failed: {str(e)}')
        traceback.print_exc()
        # Perhaps delete any existing key if conversion failed ???
        
    if stored_val is None:
        helper.log_warning(f'No StoragePassword found for {target_key}')

    return stored_val
########## -----------------------------------------------
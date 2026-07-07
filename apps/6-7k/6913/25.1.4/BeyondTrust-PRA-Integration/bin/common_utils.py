# Functions to provide common utilities to other scripts

import base64
from datetime import datetime
import traceback

LAST_EVENT_INGESTED_DATE_KEY = 'last_event_ingested_date'

########## Base64 encodes the input string
def base64_encode(input: str):
    input_bytes = input.encode('ascii')
    base64_bytes = base64.b64encode(input_bytes)
    base64_message = base64_bytes.decode('ascii')
    return base64_message
########## -----------------------------------------------


########## Retrieves the start date value from the StoragePasswords
def get_end_date(helper, default_end_date: int):
    end_date_to_use = default_end_date
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
    stored_val = get_stored_val(helper, target_key, str(default_end_date))
    
    try:
        if (stored_val is not None) and (stored_val.clear_password != None) and (stored_val.clear_password != ''):
            # use the stored val as a unix timestamp directly
            end_date_to_use = int(stored_val.clear_password)
    except Exception as e:
        helper.log_error(f'Retrieval of start date failed: {str(e)} - value will be cleared')
        traceback.print_exc()
        clear_end_date(helper)

    return end_date_to_use
########## -----------------------------------------------


########## Saves the start date value in the StoragePasswords
def save_end_date(helper, new_value: int):
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
    stored_val = get_stored_val(helper, target_key, None)
    stored_val.update(password=new_value)
########## -----------------------------------------------


########## Clears the start date value from the StoragePasswords
def clear_end_date(helper):
    target_key = f'{str(helper.get_input_stanza_names())}_{LAST_EVENT_INGESTED_DATE_KEY}'
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
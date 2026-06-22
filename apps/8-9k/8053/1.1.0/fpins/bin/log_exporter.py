import threading
import concurrent.futures

import os
import json
import sys
import datetime
import logging
import config
from token_generation import get_token, create_token
from six import PY2, iteritems
import requests

# Script version
SCRIPT_VERSION = '1.1.0'
# Set MAX Workers
MAX_WORKERS = os.cpu_count()*8
# Lock for state.db access
state_db_lock = threading.Lock()
# Lock for token refresh on 401
token_refresh_lock = threading.Lock()
# Folder containing this file
SRC_FOLDER = os.path.abspath(os.path.dirname(__file__))  # do not edit
# Folder to save state.db file
DB_PATH = os.path.join(os.path.dirname(SRC_FOLDER),
                       'local', 'state.db')  # do not edit
# API constants
API_URL_TEMPLATE = '{insights_base_url}/api/export/{point_product_code}/{collection_name}'
API_LIMIT = -1
API_AUTH_HEADER = 'Authorization'

# Define global variables
LOG_ACTION_TYPES = []
PROXIES = None


def update_state_db(collectionName, last_eventinsertedtime, last_offset):
    """Update state.db with last eventinsertedtime and offset"""
    # Serialize state.db access
    with state_db_lock:
        state = {}
        if os.path.isfile(DB_PATH):
            try:
                with open(DB_PATH, 'r') as f:
                    content = f.read().strip()
                    if content:
                        state = json.loads(content)
            except Exception:
                state = {}
        state[collectionName] = {
            'last_eventinsertedtime': last_eventinsertedtime,
            'last_offset': last_offset
        }
        with open(DB_PATH, 'w') as f:
            f.write(json.dumps(state))


def read_state_db(collectionName):
    """Read state.db and return collection_name ,last_eventinsertedtime and last_offset"""
    with state_db_lock:
        if not os.path.isfile(DB_PATH):
            logging.info(
                f"[COLLECTION: {collectionName}] State DB file not found. Returning defaults.")
            return '', 0
        with open(DB_PATH, 'r') as f:
            try:
                content = f.read().strip()
                if not content:
                    logging.warning(
                        f"[COLLECTION: {collectionName}] State DB file is empty. Returning defaults.")
                    return '', 0
                state = json.loads(content)
                entry = state.get(collectionName, {})
                logging.info(
                    f"[COLLECTION: {collectionName}] Read from state DB: {entry}")
                return entry.get('last_eventinsertedtime', ''), entry.get('last_offset', 0)
            except Exception as e:
                logging.error(
                    f"[COLLECTION: {collectionName}] Error reading state DB: {e}")
                return '', 0


def migrate_state_db(pp_config):
    """Migrate old state.db keys (collectionName) to new format (ppcode_collectionName)"""
    with state_db_lock:
        if not os.path.isfile(DB_PATH):
            return
        try:
            with open(DB_PATH, 'r') as f:
                content = f.read().strip()
                if not content:
                    return
                state = json.loads(content)
        except Exception:
            return

        migrated = False
        for pp_code, pp_data in pp_config.items():
            for col in pp_data.get('collections', []):
                new_key = "{}_{}".format(pp_code, col)
                if new_key not in state and col in state:
                    state[new_key] = state.pop(col)
                    migrated = True
                    logging.info(f"Migrated state.db key '{col}' -> '{new_key}'")

        if migrated:
            with open(DB_PATH, 'w') as f:
                f.write(json.dumps(state))
            logging.info("State DB migration complete")


def splunkFieldName(key):
    # a-z, A-Z, _ -
    key = u''.join(c for c in key if ord(c) in range(97, 123) or
                   ord(c) in range(65, 91) or ord(c) in (45, 95))
    # strip leading underbars
    key = key.lstrip('_')
    return (key)


def TranslateLogMessage(d):
    """
    Should be all unicode strings in d. Potential time stamp: _time
    Cleans keys according to Splunk fieldname syntax.
    Returns unicode string in kv-format

    TODO Add more test cases to cover all branches
    logeventdaemon -u jack@bitglass-tme.com -k Pa$$word -r :5514
    echo '<14>Jun 10 20:15:35 bitglass :{"pagetitle": "", "emailsubject": "", "action": "Expire Session", "logtype": "access", "emailbcc": "", "filename": "", "application": "Bitglass", "dlppattern": "", "location": "Almaty||Almaty||ALA||KZ", "email": "jack@bitglass-tme.com", "details": "Session Expired", "emailcc": "", "time": "02 Jul 2020 18:20:14", "emailfrom": "", "user": "Jack Jack", "syslogheader": "<110>1 2020-07-02T18:20:14.490000Z api.bitglass.com NILVALUE NILVALUE access", "device": "Ubuntu", "transactionid": "99d74ff0002be948e2b456f5e8417abf9a2a0c8b [02 Jul 2020 18:20:14]", "ipaddress": "95.59.177.29", "customer": "Bitglass", "url": "/accounts/login/", "request": "", "_time": "07/02/2020 18:20:14", "activity": "Login", "emailsenttime": "", "useragent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:77.0) Gecko/20100101 Firefox/77.0", "emailto": ""}' > /dev/udp/0.0.0.0/5514
    """

    strFormat = u''

    # for k, v in d.items():
    for k, v in iteritems(d):
        # remaining fields
        # Remove empty fields
        if v is None or v == u'':
            # Allow empty fields afterall
            # continue
            v = u'\"\"'
        sv = u'{0}'.format(v)
        # We rely on splunks default KV_MODE detection, based on key=value,
        # so need to take pre-caution for values containing = and/or ,
        if u',' in sv or u'=' in sv and sv[0] != u'\"':
            # Surround value by " if required, and remove any newlines -
            # questionable practice....
            sv = u'\"{0}\"'.format(sv)
        # Delete newlines from values - questionable practice really - we
        # should not tamper with any content....
        sv = sv.replace(u'\n', u'')
        strFormat += u',{0}={1}'.format(splunkFieldName(k), sv)
    strFormat += u',\n'

    # Skip leading comma
    if PY2:
        return strFormat[1:].encode('utf-8', 'replace')
    else:
        return strFormat[1:]


# New function to fetch data from API
def fetch_api_data(ApiUrl, collectionName, starttime, last_offset, token, exported_fields, API_TIMEOUT, instance_id, proxies=None):
    """Fetch data from API with pagination, return (results, next_offset, finished)"""
    headers = {
        'Content-Type': 'application/json',
        API_AUTH_HEADER: f'Bearer {token}'
    }

    data = {
        'instanceId': instance_id,
        'starttime': starttime,
        'offset': last_offset,
        'limit': API_LIMIT,
        'includeFields':exported_fields
    }

    logging.info(
        f"[COLLECTION: {collectionName}] Exported fields: {exported_fields}")
    if collectionName == "SWG":
        data['filters'] = {
            "act": {
                "ne": ["Allowed"]
            }
        }
    
    logging.info(
        f"[COLLECTION: {collectionName}] Sending export API request")
    try:
        response = requests.post(
            ApiUrl, headers=headers, json=data, proxies=proxies, timeout=API_TIMEOUT)
        response.raise_for_status()
        resp_json = response.json()
        results = resp_json.get('results', [])
        success = resp_json.get('result_status', '') == 'FINISHED'
        logging.info(
            f"[COLLECTION: {collectionName}] Export API response received. Records fetched: {len(results)}. Result status: {resp_json.get('result_status', '')}")
        return results, success
    except Exception as e:
        logging.error(
            f"[COLLECTION: {collectionName}] API request failed: {e}")
        raise
    

def format_json(item):
    log = {}
    for k, v in item.items():
        log[k] = v if v is not None else ''
    return log


def refresh_token_and_store(appconfig, current_token):
    """Thread-safe token refresh on 401. Returns the (possibly already-refreshed) token."""
    with token_refresh_lock:
        if getattr(appconfig, 'api_token', None) and appconfig.api_token != current_token:
            logging.info("Token already refreshed by another thread. Reusing.")
            return appconfig.api_token
        try:
            proxies = config.build_proxies_dict(appconfig.proxies)
            new_token = create_token(appconfig.api_key, appconfig.platform_base_url, proxies)
        except Exception as e:
            logging.error(f"Failed to refresh token after 401: {e}")
            return None
        if not new_token:
            logging.error("Token refresh returned empty token.")
            return None
        if appconfig.StoreToken(new_token):
            logging.info("Refreshed API token stored in Splunk storage/passwords.")
        else:
            logging.warning("Refreshed API token generated but failed to store in storage/passwords.")
        appconfig.api_token = new_token
        return new_token


def process_collection(collectionName, point_product_code, exported_fields, API_TOKEN, PROXIES, appconfig):
    start_time_utc = datetime.datetime.now(
        datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    logging.info(
        f"[COLLECTION: {collectionName}][PP_CODE: {point_product_code}] Processing started at (UTC): {start_time_utc}")
    try:
        API_URL = API_URL_TEMPLATE.format(insights_base_url=appconfig.insights_base_url,
                                          point_product_code=point_product_code, collection_name=collectionName)
        sync_interval_val = int(appconfig.sync_interval) if appconfig.sync_interval and str(
            appconfig.sync_interval).isdigit() else 20
        API_TIMEOUT = max(sync_interval_val - 10, 1)
        instance_id = appconfig.instance_id

        state_key = "{}_{}".format(point_product_code, collectionName)
        last_eventinsertedtime, last_offset = read_state_db(state_key)
        if not last_eventinsertedtime:
            last_eventinsertedtime = (datetime.datetime.now(
                datetime.timezone.utc) - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            logging.info(
                f"[COLLECTION: {collectionName}] No previous state found. Setting start time to 24 hours ago: {last_eventinsertedtime}")
            last_offset = 0

        logging.info(
            f"[COLLECTION: {collectionName}] Fetched Last event inserted time: {last_eventinsertedtime}, offset: {last_offset} From State DB")
        try:
            results, success = fetch_api_data(API_URL, collectionName, last_eventinsertedtime,
                                              last_offset, API_TOKEN, exported_fields, API_TIMEOUT, instance_id, PROXIES)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logging.warning(
                    f"[COLLECTION: {collectionName}] Got 401. Refreshing token and retrying once.")
                new_token = refresh_token_and_store(appconfig, API_TOKEN)
                if not new_token:
                    logging.error(
                        f"[COLLECTION: {collectionName}] Token refresh failed. Skipping this run.")
                    return
                # Retry ONCE with new token. Any failure here (including another 401)
                # is final — do NOT refresh again, to avoid loops.
                try:
                    results, success = fetch_api_data(API_URL, collectionName, last_eventinsertedtime,
                                                      last_offset, new_token, exported_fields, API_TIMEOUT, instance_id, PROXIES)
                except Exception as e2:
                    logging.error(
                        f"[COLLECTION: {collectionName}] Retry after token refresh failed. No further retries this run: {e2}")
                    return
            else:
                logging.error(
                    f"[COLLECTION: {collectionName}] Error fetching API data: {e}")
                return
        except Exception as e:
            logging.error(
                f"[COLLECTION: {collectionName}] Error fetching API data: {e}")
            return

        if not success:
            logging.warning(
                f"[COLLECTION: {collectionName}] API indicates incomplete data retrieval. Stopping further fetches for now.")
            return
        logging.info(
            f"[COLLECTION: {collectionName}] Fetched {len(results)} records.")
        if not results:
            logging.info(
                f"[COLLECTION: {collectionName}] No new results from API.")
            return

        max_eventinsertedtime = max(
            item.get('eventinsertedtime', '') for item in results if item.get('eventinsertedtime', ''))

        count = 0
        for item in results:
            eventinsertedtime = item.get('eventinsertedtime', '')
            if eventinsertedtime == max_eventinsertedtime:
                count += 1
            formated_item = format_json(item)
            formated_item['ppcode'] = point_product_code
            data = TranslateLogMessage(formated_item)
            sys.stdout.write(data)
            sys.stdout.flush()

        if max_eventinsertedtime == last_eventinsertedtime:
            last_offset += count
        else:
            last_offset = count
        update_state_db(state_key, max_eventinsertedtime, last_offset)
        logging.info(
            f"[COLLECTION: {collectionName}] Updated state DB with last_eventinsertedtime: {max_eventinsertedtime}, last_offset: {last_offset}")
    except Exception as e:
        logging.error(
            f"[COLLECTION: {collectionName}] Unexpected error in processing: {e}")
    finally:
        end_time_utc = datetime.datetime.now(
            datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(
            f"[COLLECTION: {collectionName}] Processing ended at (UTC): {end_time_utc}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s - %(message)s')
    logging.info(f"Starting  Log Exporter version {SCRIPT_VERSION}")
    if not os.path.isfile(DB_PATH):
        with open(DB_PATH, 'w') as f:
            f.write('')
    appconfig = config.Config()
    isConfig = appconfig.LoadConfiguration()
    if not isConfig:
        logging.error("Error loading configuration in log export api.")
        os._exit(1)
    PROXIES = config.build_proxies_dict(appconfig.proxies)
    pp_config = appconfig.pp_config

    if not pp_config:
        logging.error("No PP codes configured in pp_config. Please run the setup page.")
        os._exit(1)

    # Migrate old state.db keys to new composite format
    migrate_state_db(pp_config)

    try:
        API_TOKEN = get_token(appconfig)
    except Exception as e:
        logging.error(f"Failed to get API token: {e}")
        os._exit(1)

    logging.info(f"[PP_CONFIG] Export process started with {len(pp_config)} PP code(s).")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for pp_code, pp_data in pp_config.items():
            collections = pp_data.get('collections', [])
            exported_fields = pp_data.get('exportedFields', 'all')
            logging.info(f"[PP_CODE: {pp_code}] Collections: {collections}, Exported Fields: {exported_fields}")
            for col_name in collections:
                futures.append(executor.submit(
                    process_collection, col_name, pp_code, exported_fields,
                    API_TOKEN, PROXIES, appconfig
                ))
        concurrent.futures.wait(futures)
    logging.info(f"[PP_CONFIG] All collections processed. Exiting...")
    os._exit(0)

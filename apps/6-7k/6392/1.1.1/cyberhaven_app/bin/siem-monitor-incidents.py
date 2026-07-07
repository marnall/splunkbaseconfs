import time
import argparse
import base64
import copy
import json
import logging
import logging.handlers
import sys,os
from datetime import datetime, timedelta
import splunk.entity as entity
import requests
import utils
import csv

def setup_logger(level):
     logger = logging.getLogger('cyberhaven_app')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/cyberhaven_app.log', maxBytes=25000000, backupCount=5)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
     logger.addHandler(file_handler)
     return logger

logger = setup_logger(logging.INFO)

def getCredentials(sessionKey):
    myapp = 'cyberhaven_app'
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,owner='nobody', sessionKey=sessionKey)
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

    for i, c in entities.items():
        if c['clear_password']:
            json_data = json.loads(c['clear_password'])
            return json_data

        raise Exception("No credentials have been found")

def current_time_ms():
    return round(time.time() * 1000)

now = current_time_ms()

def is_finished():
    global now
    return current_time_ms() - now >= 55_000

parser = argparse.ArgumentParser(
    description='Fetches Cyberhaven incidents and logs them')
parser.add_argument(
    "--replay-old", help="replay already existing incidents", default=False,  action='store_true')
parser.add_argument(
    "--no-verify", help="allow insecure requests", default=False,  action='store_true')

args = parser.parse_args()

sessionKey = sys.stdin.readline().strip()

AUTH_PATH = "/user-management/auth/token"
ALERTS_PATH = "/v1/risky-dashboard/incident/list-siem"

creds = getCredentials(sessionKey)
AUTH = creds.get('token')
HOST = creds.get('host')

API_PATH = "https://"+HOST
REPLAY_OLD = args.replay_old
# verify ssl certificate
VERIFY = not args.no_verify

old_time = "2001-01-01T00:00:00Z"
nowTimeISO = datetime.utcnow().isoformat() + "Z"
# if we replay old events then start set day to something in the past
if args.replay_old:
    nowTimeISO = old_time

# incidents default request data
incidents_request_data = {
    # amount of entities to fetch
    "page_size": 1000,
    "sort_desc": False,
    "sort_by": "event_time",
    "filters": {
         "times_filter": {
            "end_time": "2090-09-01T23:59:59Z",
#             "start_time": nowTimeISO
        }
    }
}

def authenticate_request(base64_creds):
    """request to fetch auth token"""
    creds_json = base64.decodebytes(bytes(base64_creds, 'utf8'))
    creds = json.loads(creds_json)
    r = requests.post(url=API_PATH + AUTH_PATH,
                      verify=VERIFY,
                      data=creds, headers={'HOST': HOST})
    r.raise_for_status()
    return r.content.decode("utf-8")


def incidents_request(token, start_time, size, search_after = ""):
    """
    request to fetch incidents
    token is authentication token returned by auth request
    page_id is pagination cursor
    """
    request_data = copy.deepcopy(incidents_request_data)
    request_data.update({'page_id': search_after, 'page_size': size })

    request_data["filters"]["times_filter"]["start_time"]  = start_time or old_time

    if search_after:
        request_data["filters"]["times_filter"]["start_time"] = old_time

    auth_header = 'Bearer {}'.format(token)

    r = requests.post(url=API_PATH + ALERTS_PATH, json=request_data,
                      verify=VERIFY,
                      headers={'authorization': auth_header, 'content-type': 'application/json;;charset=UTF-8'})
    if r.status_code == 401:
        logger.info("Not authenticated")
    if r.status_code >= 400:
        logger.info(r.text)
        exit(0)
    json_data = r.json()
    records = json_data.get("incidents", None)
    return {
        'alerts': records,
        'next_page_id': json_data.get('next_page_id', '')
    }


def log_events(events):
    file_path = os.environ['SPLUNK_HOME'] + '/var/log/splunk/incidents.csv'
    file_exists = os.path.isfile(file_path)
    
    logger.info("Added " + str(len(events)) + " new incidents")

    parsed_events = []
    for event in events:
        data = utils.format_event(event)
        parsed_events.append(data)

    if not parsed_events:
        return

    with open(file_path, 'a', encoding='UTF8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=parsed_events[0].keys(), delimiter=',', lineterminator='\n')

        if not file_exists:
            writer.writeheader()
        writer.writerows(parsed_events)
    

class LastIncidentObjectPersisted:
    current = ''
    file = None
    mode = ''

    def __init__(self, path):
        self.path = path
        self.mode = 'r+' if os.path.exists(path) else 'w+'

    def get(self):
        self.file = open(self.path, self.mode)
        self.current = self.file.read()
        """return persisted value"""
        strippedValue = self.current.strip()
        data = strippedValue.split("_")
        search_after = ""
        start_time = ""
        if len(data) >= 1:
            start_time = data[0]
        if len(data) == 2:
            search_after = data[1]

        self.file.close()
        return {
            'search_after': search_after,
            'start_time': start_time
        }

    def set(self, start_time, search_after):
        self.file = open(self.path, self.mode)
        self.current = self.file.read()
        """set value to file"""
        formatedValue = "{}_{}".format(start_time, search_after)
        self.file.seek(0)
        self.file.truncate(0)
        self.file.write(formatedValue)
        os.fsync(self.file)
        self.current = formatedValue
        self.file.close()

one_ms = timedelta(0, 0, 1000)

def parse_nano_date(str):
    arr = str.replace("Z", "").split(".")
    d = datetime.fromisoformat(arr[0])
    if (len(arr) > 1):
        msStr = arr[1]
        msStr = msStr + "0" * (6 - len(msStr))
        ms = int(msStr[0:6])
        d = d.replace(microsecond=ms)
    return d

def main():
    token = authenticate_request(AUTH)

    while True:
        last_incident_id_store = LastIncidentObjectPersisted(os.environ['SPLUNK_HOME'] + '/var/log/splunk/incidents.state')
        persisted_value = last_incident_id_store.get()

        events = incidents_request(token, persisted_value['start_time'], size=1000, search_after=persisted_value["search_after"])
        alerts = events["alerts"]

        if len(alerts) == 0 or is_finished():
            break

        logger.info(parse_nano_date(alerts[-1]['event_time']) + one_ms)
        logger.info(parse_nano_date(alerts[-1]['event_time']))

        if persisted_value['start_time'] == "":
            d = parse_nano_date(alerts[-1]['event_time']) + one_ms
            last_incident_id_store.set(d, '')
            persisted_value['start_time'] = d

        if  events["next_page_id"] == '':
            # take date, remove Z at the end and add one second and then bring back Z at the end
            # api and python iso formats are different
            # in case we reached end of the list we want to store time of last event and use it in order to continue pagination
            d = parse_nano_date(alerts[-1]['event_time']) + one_ms
            result_date = d.isoformat() + "Z"
            last_incident_id_store.set(result_date, events["next_page_id"])
        else:
            last_incident_id_store.set(persisted_value['start_time'], events["next_page_id"])

        log_events(alerts)

if __name__ == '__main__':
    main()

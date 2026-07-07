import json
import sys
import traceback
import time
import hmac
import re
import os
import hashlib
import base64
import requests
from urllib.parse import quote, quote_plus, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client

BATCH_SIZE = 10

OK = 0
ERROR_CODE_UNKNOWN = 1
ERROR_CODE_VALIDATION_FAILED = 2
ERROR_CODE_CHANNEL_NOT_FOUND = 3
ERROR_CODE_FORBIDDEN = 4
ERROR_CODE_HTTP_FAIL = 5
ERROR_CODE_UNEXPECTED = 6


def log(msg, *args):
    sys.stderr.write(msg + " ".join([str(a) for a in args]) + "\n")


def validate_payload(payload):
    if 'configuration' not in payload:
        log("FATAL Invalid payload, missing 'configuration'")
        return False

    config = payload.get('configuration')

    if not config.get('alert_name'):
        log("FATAL Validation Error: Parameter alert_name is missing or empty")
        return False

    return True


def get_eventhub_cs(payload):
    service = client.Service(
        token=payload.get('session_key'),
        owner='nobody',
        app='Splunk_TA_Salem'
    )
    password_xml = service.storage_passwords.get("hub:salem:")['body'].read().decode('utf-8')
    cs = re.search('\s*<s:.*?name="clear_password">(.*?)<.*?>', password_xml)
    return cs.group(1)


def get_connection(payload):
    event_hub_cs = get_eventhub_cs(payload)
    event_hub_details = {}
    for item in event_hub_cs.split(';'):
        k, v = item.split('=', 1)
        event_hub_details[k] = v

    if not event_hub_details.get('Endpoint'):
        raise ValueError("Salem Event Hub Connection String malformed or empty. Return to Splunk_TA_Salem app setup")

    event_hub_details['Endpoint'] = 'https' + event_hub_details['Endpoint'][2:]

    if not is_https(event_hub_details['Endpoint']):
        raise ValueError('Salem Event Hub URL must use https protocol')

    connection = build_auth_signature(
        event_hub_details['Endpoint'],
        event_hub_details['EntityPath'],
        event_hub_details['SharedAccessKeyName'],
        event_hub_details['SharedAccessKey']
    )
    return connection


def build_auth_signature(sb_name, eh_name, sas_name, sas_value):
    """
    Returns an authorization token dictionary
    for making calls to Event Hubs REST API.
    """
    uri = quote_plus(sb_name + eh_name)
    sas = sas_value.encode('utf-8')
    expiry = str(int(time.time() + 10000))
    string_to_sign = (uri + '\n' + expiry).encode('utf-8')
    signed_hmac_sha256 = hmac.HMAC(sas, string_to_sign, hashlib.sha256)
    signature = quote(base64.b64encode(signed_hmac_sha256.digest()))
    return {
        "sb_name": sb_name,
        "eh_name": eh_name,
        "token": f'SharedAccessSignature sr={uri}&sig={signature}&se={expiry}&skn={sas_name}'
    }


def is_https(url):
    """Checks if the given URL uses HTTPS protocol.
    Args:
        url: The URL string to validate.

    Returns:
        True if the URL uses HTTPS, False otherwise.
    """
    parsed_url = urlparse(url)
    return parsed_url.scheme == "https"


def build_salem_alert(event, config):
    alert = {
        "source": config['alert_source'] if config.get('alert_source') else "Splunk",
        "alert_name": config['alert_name'],
        "alert": event
    }
    if config.get('alert_id') and config.get('alert_id') != 'null':
        alert['id'] = config['alert_id']
    return alert


def send_salem_alert(payload):
    try:
        if not validate_payload(payload):
            raise ValueError("payload malformed")
        config = payload.get('configuration')
        events = payload.get('result', dict())
        connection = get_connection(payload)
        batch = []
        if config.get('aggregate') == 'aggregate' or isinstance(events, dict):
            alert = build_salem_alert(events, config)
            batch.append({'body': json.dumps(alert)})
            send_batch(connection, batch)
        else:
            for event in events:
                alert = build_salem_alert(event, config)
                batch.append({'body': json.dumps(alert)})
                if len(batch) >= BATCH_SIZE:
                    # EventDataBatch object reaches max_size.
                    send_batch(connection, batch)
                    batch = []
            send_batch(connection, batch)
        return OK

    except Exception:
        log("FATAL Unexpected error:", sys.exc_info()[0])
        track = traceback.format_exc()
        log(track)
        return ERROR_CODE_UNEXPECTED


def send_batch(connection, batch):
    headers = {
        'Authorization': connection['token'],
        'Content-Type': 'application/vnd.microsoft.servicebus.json'
    }
    data = json.dumps(batch)
    url = connection['sb_name'] + connection['eh_name'] + '/messages'
    res = requests.post(
        url,
        headers=headers, data=data
    )
    if res.status_code != 201:
        raise Exception(f'Salem Event Hub ({url}) responded with status code: {res.status_code}, msg: {res.text}')


if __name__ == '__main__':
    log("INFO Running python %s" % (sys.version_info[0]))
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        result = send_salem_alert(payload)
        if result == OK:
            log("INFO Successfully sent alert to Salem")
        else:
            log("FATAL Alert action failed")
        sys.exit(result)

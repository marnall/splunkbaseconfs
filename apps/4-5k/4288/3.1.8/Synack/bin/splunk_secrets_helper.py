import sys
import splunk.entity as entity

def fetch_synack_api_token():
    try:
        session_key = sys.stdin.readline().strip()
        entities = entity.getEntities(['admin', 'passwords'], namespace='Synack', owner='nobody', sessionKey=session_key)
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % ('Synack', str(e)))

    for i, password in entities.items():
        if password['realm'] == 'synack' and password['username'] == 'synack-integration':
            return password['clear_password']

    raise Exception("Synack API token couldn't be found")

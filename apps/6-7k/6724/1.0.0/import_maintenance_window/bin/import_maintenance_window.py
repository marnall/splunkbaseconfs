import sys
import json
import csv
import gzip
from collections import OrderedDict
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError

def send_webhook_request(url, body, session_key,user_agent=None):
    if url is None:
        sys.stderr.write("ERROR No URL provided\n")
        return False
    sys.stderr.write("INFO Sending POST request to url=%s with size=%d bytes payload\n" % (url, len(body)))
    sys.stderr.write("DEBUG Body: %s\n" % body)
    try:
        if sys.version_info >= (3, 0) and type(body) == str:
            body = body.encode()
        auth = "Splunk " + session_key
        req = Request(url, body, {"Authorization": auth, "Content-Type": "application/json", "User-Agent": user_agent})
        res = urlopen(req)
        if 200 <= res.code < 300:
            sys.stderr.write("INFO Webhook receiver responded with HTTP status=%d\n" % res.code)
            sys.stderr.write("INFO Webhook receiver response=%s\n" % res.read().decode('utf-8'))
            return True
        else:
            #sys.stderr.write("ERROR Webhook receiver responded with HTTP status=%d\n" % res.code)
            sys.stderr.write("ERROR Webhook receiver response=%s\n" %  res.read().decode('utf-8'))
            return False
    except HTTPError as e:
        sys.stderr.write("ERROR Error sending webhook request: %s\n" % e)
    except URLError as e:
        sys.stderr.write("ERROR Error sending webhook request: %s\n" % e)
    except ValueError as e:
        sys.stderr.write("ERROR Invalid URL: %s\n" % e)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        sys.stderr.write("FATAL Unsupported execution mode (expected --execute flag)\n")
        sys.exit(1)
    try:
        #Load settings and extract configuration
        settings = json.loads(sys.stdin.read())
        title = settings['configuration'].get('title')
        description = settings['configuration'].get('description')
        start_time = settings['configuration'].get('start_time')
        end_time = settings['configuration'].get('end_time')
        object_type = settings['configuration'].get('object_type')
        object_keys = settings['configuration'].get('object_keys').split(',')
        
        #Loop over each key, and append in the Object Type
        object_array = []
        for key in object_keys:
          temp_object = OrderedDict(
              object_type = object_type,
              _key = key
          )
          object_array.append(temp_object)

        # URL for the maintenance window interface. See https://docs.splunk.com/Documentation/ITSI/4.14.2/RESTAPI/ITSIRESTAPIreference#Maintenance_Services_Interface
        url = "https://localhost:8089/servicesNS/nobody/SA-ITOA/maintenance_services_interface/maintenance_calendar"
        
        session_key = settings.get('session_key')
        body = OrderedDict(
            title = title,
            comment = description,
            start_time = start_time,
            end_time = end_time,
            objects = object_array
        )
        user_agent = 'Splunk'
        if not send_webhook_request(url, json.dumps(body), session_key, user_agent=user_agent):
            sys.exit(2)
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s\n" % e)
        sys.exit(3)

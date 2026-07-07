#   SPlunk application for sending alerts from Splunk to Activu via Webhook with additional fields and payload
#   Developed by Visibility Platforms
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import sys, json, requests
from splunk.clilib import cli_common as cli

def send_alert_data(alert):
    elements = alert.pop('configuration')

    #   Getting URL to send the alert. Note: for Splunk Cloud vetting, URLs must start with https://
    url = ''
    if 'base_url' in elements:
      url = elements['base_url']

    if url == None or not url.startswith('https://'):
      #   No valid URL in the alert parameters, trying app configuration next
      cfg = cli.getConfStanza('alert_actions','Activu')
      url = cfg.get('param.base_url')
      if url == None or not url.startswith('https://'):
        #   No valid URL in the configuration either - exiting
        print("ERROR No valid https URL found in the alert parameters or Activu app configuration! Exiting.", file=sys.stderr)
        sys.exit(2)

    #   Getting list of optional URLs to add to the alert payload.
    if 'urls' in elements:
      alert['urls'] = elements['urls'].replace("\nhttp", "^http").split('^')
    else:
      alert['urls'] = ['']

    #   Getting Activu alert name (Activu action) to add to the alert payload.
    if 'alert_name' in elements:
      alert['alert_name'] = elements['alert_name']
    else:
      alert['alert_name'] = 'Default'

    #   Sending the alert to Activu webhook.
    try:
        temp = json.dumps(alert)
        alert = temp.replace("'", '"')
        headers = {'Content-type': 'application/json'}
        res = requests.post(url=url, data=alert, headers = headers, verify=False)
        print("INFO Status code: %s" % res.status_code, file=sys.stderr)
        return 200 <= res.status_code < 300
    except requests.exceptions.RequestException as e:
        print("ERROR Error sending message: %s" % e, file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        if not send_alert_data(payload):
            print("ERROR Failed trying to send alert notification", file=sys.stderr)
            sys.exit(2)
        else:
            print("INFO alert notification successfully sent", file=sys.stderr)
    else:
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)

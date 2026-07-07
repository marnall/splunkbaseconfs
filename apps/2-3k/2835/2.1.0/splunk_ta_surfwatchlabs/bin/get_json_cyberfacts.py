import datetime, json, requests, os.path as op, time
import ConfigParser


config = ConfigParser.SafeConfigParser()
file_dir = op.join(op.dirname(op.dirname(op.abspath(__file__))), 'local')
conf = op.join(file_dir, "sw_api.conf")
config.read(conf)
app_id = config.get('swl_account', 'app_id')
app_key = config.get('swl_account', 'app_key')


# TODO : use splunk.Intersplunk.readResults instead of just printing to stdout

yesterday_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=1)

url = 'https://www.surfwatchlabs.com/api/v3/cyberFacts'
headers = {'app-id': app_id, 'app-key': app_key, 'accept': 'application/json'}
payload = {'startDate': yesterday_datetime.date(), 'endDate': yesterday_datetime.date()}

r = requests.get(url, headers=headers, params=payload)

if r.status_code == requests.codes.ok:

    j = r.json()
    for cyberfact in j:
        print json.dumps(cyberfact)
        print '\n'

else:
    # TODO: handle error as needs dictate
    r.raise_for_status()

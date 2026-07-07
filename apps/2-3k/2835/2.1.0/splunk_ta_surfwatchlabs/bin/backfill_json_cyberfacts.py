import datetime, json, requests, os.path as op, time
import ConfigParser

def query_for_cyberfacts(app_id, app_key, start_datetime, end_datetime):
    url = 'https://www.surfwatchlabs.com/api/v3/cyberFacts'
    headers = {'app-id': app_id, 'app-key': app_key, 'accept': 'application/json'}
    payload = {'startDate': start_datetime, 'endDate': end_datetime}

    # TODO : use splunk.Intersplunk.readResults instead of just printing to stdout

    r = requests.get(url, headers=headers, params=payload)
    if r.status_code == requests.codes.ok:

        j = r.json()
        for cyberfact in j:
            print json.dumps(cyberfact)
            print '\n'

    else:
        # TODO: handle error as needs dictate
        r.raise_for_status()


def backfill(app_id, app_key):

    curr_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=1)

    # final_date = datetime.datetime(2015, 7, 18)
    final_date = datetime.datetime(2014, 1, 1)
    while (curr_datetime >= final_date):
        query_for_cyberfacts(app_id, app_key, curr_datetime.date(), curr_datetime.date())
        curr_datetime -=  datetime.timedelta(days=1)
        time.sleep(5)  #sleep to not exceed request limit


config = ConfigParser.SafeConfigParser()
file_dir = op.join(op.dirname(op.dirname(op.abspath(__file__))), 'local')
conf = op.join(file_dir, "sw_api.conf")
config.read(conf)
app_id = config.get('swl_account', 'app_id')
app_key = config.get('swl_account', 'app_key')
backfill(app_id, app_key)

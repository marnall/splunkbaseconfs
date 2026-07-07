from splunk.clilib import cli_common as cli
import http.client
import json
from os.path import join
import splunk.mining.dcutils as dcu
import splunk.Intersplunk

logger = dcu.getLogger()
logger.info('todayseues')

data, dummy2, settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")
# Get the EUEs scheduled in the last 24 hours

# warning: following line will be modified by cloud-convert.sh when building for cloud
cfg = cli.getConfStanza('2steps', 'twostepscloud')


hostname = cfg.get('hostname')
port = cfg.get('port')
url = hostname + ":" + port
path = cfg.get('path')

conn = http.client.HTTPSConnection(url)
reqUrl = join(path, "schedules")

logger.info('requesting schedules from: ' + url + reqUrl)
conn.request("GET", reqUrl, None,
             {"Authorization": "2steps " + sessionKey})
r = conn.getresponse()
res = r.read()
jres = json.loads(res)

lookup = {}

id_names = {}
for eue in jres["tests"]:
    id_names[ eue["eue_id"] ] = eue["eue_name"]

active = {}
try:
    for eue, schedules in jres["schedules"].items():
        for sch in schedules:
            if sch["scheduledInPast24Hours"] and sch["active"]:
                name = id_names[eue]
                active[name] = 1

except Exception as e:
    logger.info('error ' + e);

logger.info('Scheduled tests for today are ' + json.dumps(active))

results = []
for row in data:
    # if the row is in the tests scheduled today, add to results, otherwise ignore
    if row["EUE"] in active:
        row["eue_status"] = 1
        results.append(row)
splunk.Intersplunk.outputResults(results)

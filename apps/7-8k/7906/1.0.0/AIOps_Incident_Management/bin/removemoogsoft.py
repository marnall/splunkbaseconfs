import sys
import csv
import json
import splunk.Intersplunk
from future.moves.urllib import request
from future.moves.urllib.parse import urlencode

def log(data):
    sys.stderr.write(data)

def main():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    headers = {'Authorization': "Splunk {}".format(str(settings.get('sessionKey')))}

    for result in results:
        actions = result.get('actions', "")

        actions = actions.replace("AIOps_Incident_Management_Integration", "")

        result['actions'] = actions

        search_url = result.get('id').replace("http://","https://")
        url = "{}?{}".format(search_url, urlencode({'actions': actions}))

        req = request.Request(url, b"", headers)
        res = request.urlopen(req)

        log("response=%s" % res)

    splunk.Intersplunk.outputResults(results)

if __name__ == "__main__":
    log("Started removedellaiopsimevent command")

    try:
        main()
    except:
        import traceback
        stack =  traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))



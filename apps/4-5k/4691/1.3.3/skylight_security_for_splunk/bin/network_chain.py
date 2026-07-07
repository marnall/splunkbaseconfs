from splunk.persistconn.application import PersistentServerConnectionApplication
import os
import re
import sys
import json

if sys.version_info[0] < 3:
    py_version = "aob_py2"
else:
    py_version = "aob_py3"

app_name = 'skylight_security_for_splunk'
pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path) or app_name in path]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), app_name, py_version]))
sys.path = new_paths

import splunklib.client as client
import splunklib.results as results

class ChainHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

        self.service = lambda token : client.connect(app=app_name, token=token)

    def handle(self, args):
        payload = json.loads(args)
        query = payload['query']
        token = payload["session"]["authtoken"]

        if query[0][0] == 'getChain':
            ip = query[0][1]
            earliest = query[1][1]
            latest = query[2][1]
            site = query[3][1]

            return self.getChain(ip=ip, earliest=earliest, latest=latest, site=site, service=self.service(token))
        else:
            query += "Bad action"
            return {"payload": query, "status": 402}

    def getChain(self, ip, earliest, latest, site, service, result=[]):
        rangedata = []

        def getFirstEvent(source):
            for i in result:
                if i["all.dest_ip"] == source or i["all.src_ip"] == source:
                    return [int(i["all.time"]), source]
            return False
 
        def getSourceChain(event):
            for i in result:
                if i["all.dest_ip"] == event[1]:
                    rangedata.append([int(i["all.time"]), i["all.src_ip"], i["all.dest_ip"]])

        def getDestinationChain(event, from_id):
            for idx, i in enumerate(result[from_id:]):
                if i["all.src_ip"] == event[1] and int(i["all.time"]) >= event[0]:
                    rangedata.append([int(i["all.time"]), i["all.src_ip"], i["all.dest_ip"]])
                    getDestinationChain(i["all.dest_ip"], idx+1)

        jobs = service.jobs
        search = "| tstats summariesonly=t count from datamodel=Skylight_Network_Traffic.all where host={} by all.time, all.src_ip, all.dest_ip | fields all.time, all.src_ip, all.dest_ip | sort 0 + all.time".format(site)
        kwargs_export = {
            "earliest_time": earliest,
            "latest_time": latest,
            "search_mode": "normal"
        }
        job = jobs.export(search, **kwargs_export)

        result = [result for result in results.ResultsReader(job)]
        del result[0:3]

        current_event = getFirstEvent(ip)
        if current_event:
            getSourceChain(current_event)
            getDestinationChain(current_event, 0)

            out_data = {
                "rangedata": rangedata
            }

            return {"payload": "{}".format(json.dumps(out_data)), "status": 200}

        return {"payload": "Empty result for this IP", "status": 200}

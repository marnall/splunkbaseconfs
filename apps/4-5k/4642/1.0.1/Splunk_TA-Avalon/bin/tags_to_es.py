import sys,re
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration
from time import sleep
import splunklib.results as results

@Configuration()
class TagsToEs(StreamingCommand):
    def stream(self, records):
        tags_selected = []
        querybit = " | where workspace.id=null "
        for record in records:
            tags_selected.append(record['selection'])
        if len(tags_selected) > 0:
            querybit = "| where "
            for i in tags_selected:
                querybit = querybit + ' tags="' + i + '" OR'
            querybit = querybit[:-2]
            wholequerybit = 'search `avalon_index` earliest=1 latest=now |dedup workspace.id '+ '|spath nodes{} output=nodes '+ '|spath workspace output=workspace '+ '| mvexpand nodes '+ '|eval _raw=nodes+workspace '+ '|spath node output=Node '+ '|spath tags{} output=tags  '+ '|mvexpand tags '+ '|spath nodeType output="NodeType" '+ '|where NodeType="ip"  '+ querybit+ '| table Node '+ '|dedup Node '+ '|rename Node as ip ' + '| outputlookup local_ip_intel.csv'
            kwargs_normalsearch = {"exec_mode": "normal", "count": 0}
            job = self.service.jobs.create(wholequerybit, **kwargs_normalsearch)
            while True:
                while not job.is_ready():
                    pass
                stats = {"isDone": job["isDone"],
                         "doneProgress": float(job["doneProgress"])*100,
                          "scanCount": int(job["scanCount"]),
                          "eventCount": int(job["eventCount"]),
                          "resultCount": int(job["resultCount"])}

                status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                          "%(eventCount)d matched   %(resultCount)d results") % stats
                if stats["isDone"] == "1":
                    break
                sleep(2)
            for result in results.ResultsReader(job.results()):
                yield {"Indicator type": 'IP',"Indicator added":result['ip']}


            #####DOMAIN#####
            wholequerybit = 'search `avalon_index` earliest=1 latest=now|dedup workspace.id '+ '|spath nodes{} output=nodes '+ '|spath workspace output=workspace '+ '| mvexpand nodes '+ '|eval _raw=nodes+workspace '+ '|spath node output=Node '+ '|spath tags{} output=tags  '+ '|mvexpand tags '+ '|spath nodeType output="NodeType" '+ '|where NodeType="domain"  '+ querybit+ '| table Node '+ '|dedup Node '+ '|rename Node as domain ' + '| outputlookup local_domain_intel.csv'
            kwargs_normalsearch = {"exec_mode": "normal", "count": 0}
            job = self.service.jobs.create(wholequerybit, **kwargs_normalsearch)
            while True:
                while not job.is_ready():
                    pass
                stats = {"isDone": job["isDone"],
                         "doneProgress": float(job["doneProgress"])*100,
                          "scanCount": int(job["scanCount"]),
                          "eventCount": int(job["eventCount"]),
                          "resultCount": int(job["resultCount"])}

                status = ("\r%(doneProgress)03.1f%%   %(scanCount)d scanned   "
                          "%(eventCount)d matched   %(resultCount)d results") % stats
                if stats["isDone"] == "1":
                    break
                sleep(2)
            for result in results.ResultsReader(job.results()):
                yield {"Indicator type": 'Domain',"Indicator added":result['domain']}
        else:
            yield {"Command result": 'No Tags selected, plese select tags from ES integration Dashboard.    '}


if __name__ == "__main__":
    dispatch(TagsToEs, sys.argv, sys.stdin, sys.stdout, __name__)
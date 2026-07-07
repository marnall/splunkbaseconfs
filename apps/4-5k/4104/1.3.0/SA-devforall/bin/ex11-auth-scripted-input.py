import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
def add_to_sys_path(paths, prepend=False):
    for path in paths:
        if prepend:
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)
        elif not path in sys.path:
            sys.path.append(path)

def add_python_version_specific_paths():
    '''
        Adds extra paths for libraries specific to Python2 or Python3,
        determined at a runtime
    '''
    # We should not rely on core enterprise packages:
    if sys.version_info >= (3, 0):
        add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py3'])], prepend=True)
    else:
        add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py2'])], prepend=True)
    # Common libraries like future
    add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py23'])], prepend=True)
    from six.moves import reload_module
    try:
        if 'future' in sys.modules:
            import future
            reload_module(future)
    except Exception:
        '''noop: future was not loaded yet'''
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py23', 'splunklib'])], prepend=True)
add_python_version_specific_paths()

  
import splunklib.results as results
import splunklib.client as client
import time
import sys
import json
from datetime import datetime

sessionKey = ""

for line in sys.stdin:
  sessionKey = line

import splunk.entity, splunk.Intersplunk
settings = dict()
records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace='SA-devforall', sessionKey=sessionKey, owner='-')
mydict = dict()
mydict = entity
myPort = mydict['mgmtHostPort']


service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user="admin")
kwargs_normalsearch = {"exec_mode": "normal", "app": "SA-devforall"}

searchquery_normal = 'search index=_audit info=completed action=search total_run_time total_run_time=* earliest=-1h@h latest=@h | stats sum(total_run_time) as total_run_time count as num_searchs sum(scan_count) as scan_count sum(event_count) as event_count sum(result_count) as result_count by user | sort 10 -total_run_time'
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
while True:
    job.refresh()
    if job["isDone"] == "1":
        break
    time.sleep(1)


if str(job["resultCount"]) == "0":
    sys.stdout.write("\n[" + str( time.time() ) + "] No Searches Run in Time Window")



for result in results.ResultsReader(job.results()):
    result['_time'] = time.time()
    sys.stdout.write("\n" + json.dumps(result, sort_keys=True))
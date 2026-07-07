#!/usr/bin/python
from __future__ import print_function

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

import json, csv, re, os
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse
import sys
import time
import splunklib.results as results
import splunklib.client as client
from io import open

# First we pull the some data from the incoming tokens. There are, I'm sure, better ways to do this... but this has worked for me for 4 years so let it roll!
sessionKey = ""
owner = "" 
app = "" 
for line in sys.stdin:
  m = re.search("sessionKey:\s*(.*?)$", line)
  if m:
          sessionKey = m.group(1)
  m = re.search("owner:\s*(.*?)$", line)
  if m:
          owner = m.group(1)
  m = re.search("namespace:\s*(.*?)$", line)
  if m:
          app = m.group(1)


# Now we detect the splunkd port, so we can define the base_url. 
import splunk.entity, splunk.Intersplunk
settings = dict()
records = splunk.Intersplunk.readResults(settings = settings, has_header = True)
entity = splunk.entity.getEntity('/server','settings', namespace=app, sessionKey=sessionKey, owner='-')
mydict = dict()
mydict = entity
myPort = mydict['mgmtHostPort']
base_url = "https://127.0.0.1:" + myPort

SH=""
if "SPLUNK_HOME" in os.environ:
                SH = os.environ['SPLUNK_HOME']

#This is how we run a normal Splunk search (more commonly used)
service = client.Service(token=sessionKey, host="127.0.0.1", port=myPort, user=owner)
kwargs_normalsearch = {"exec_mode": "normal", "app": app}
searchquery_normal = '| rest /servicesNS/-/SA-devforall/data/ui/views | search eai:acl.app="SA-devforall" eai:data="* class=\\"files\\"*" | table title label eai:data | rex mode=sed field="eai:data" "s/\\s/ /g" | rex field="eai:data" "(?<contents><ul class=\\"files\\".*?)</ul>" | rex max_match=15 field="contents" "<li>(?<file>.*?)</li>" | eval file=mvfilter(NOT like(file, "%.xml")), file=mvjoin(mvfilter(NOT like(file,"%/")),";") | rename eai:data as xml | fields - contents  '
job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)
while True:
    job.refresh()
    if job["isDone"] == "1":
        break
    time.sleep(0.1)

print("title,label,xml,file")
for item in results.ResultsReader(job.results()):
    files = ""
    if "file" in item: 
        fileElements = item['file'].split(";")
        if len(fileElements) > 0:
            for file in item['file'].split(";"):
                try:
                    with open(SH + "/etc/apps/" + app + "/" + file) as f:
                        path = SH + "/etc/apps/" + app + "/" + file
                        files +=  "// START FILE\n// Path: " + path + "\n//\n"
                        lines = f.readlines()
                        files += "\n".join(lines)
                        f.close()
                except:
                    print("error with " + file)
    print('"' + str(item['title']).replace('"', '""') + '","' + item['label'].replace('"', '""') + '","' + item['xml'].replace('"', '""') + '","' + files.replace('"', '""') + '"')

#End normal Splunk search

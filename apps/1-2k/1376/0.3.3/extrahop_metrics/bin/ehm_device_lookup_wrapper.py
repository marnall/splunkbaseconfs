import os
import sys
import subprocess

import splunk.bundle as bundle

'''
wrapper script used to call script that gets the OID and friendly names from the configured Extrahop device.
if there is an error, ie. authentication, exit script with status 1 and print out stdout from child process
'''

sessionKey = sys.stdin.readline()

app = bundle.getConf('app',sessionKey=sessionKey, namespace='extrahop_metrics', owner='nobody')

python_path = app['extrahop_metrics']['python_path']

_NEW_PYTHON_PATH = python_path
_SPLUNK_PYTHON_PATH = os.environ['PYTHONPATH']

os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH 
my_process = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','extrahop_metrics','bin','ehm_device_lookup.py')

p = subprocess.Popen([os.environ['PYTHONPATH'],
                      my_process,app['extrahop_metrics']['username'],
                      app['extrahop_metrics']['password'],
                      app['extrahop_metrics']['hostname'],
                      os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','extrahop_metrics','lookups')], 
                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = p.communicate()[0]
result = p.returncode
if result != 0:
    print output
    sys.exit(1)
else:
    print output
    sys.exit(0)
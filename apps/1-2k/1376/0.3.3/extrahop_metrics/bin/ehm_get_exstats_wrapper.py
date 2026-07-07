import os
import sys
import subprocess
import splunk.entity as entity
import splunk.bundle as bundle

'''wrapper script used to gather metrics from the Extrahop device via API call'''

sessionKey = sys.stdin.readline().strip()
app = bundle.getConf('app',sessionKey=sessionKey, namespace='extrahop_metrics', owner='nobody')
inputs = bundle.getConf('inputs',sessionKey=sessionKey, namespace='extrahop_metrics', owner='nobody')

python_path = app['extrahop_metrics']['python_path']

_NEW_PYTHON_PATH = python_path
_SPLUNK_PYTHON_PATH = os.environ['PYTHONPATH']

os.environ['PYTHONPATH'] = _NEW_PYTHON_PATH 
my_process = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','extrahop_metrics','bin','ehm_get_exstats.py')

script_name = 'script://'+os.path.join('.','bin','ehm_get_exstats_wrapper.py')

p = subprocess.Popen([os.environ['PYTHONPATH'],
                    my_process,app['extrahop_metrics']['username'],
                    app['extrahop_metrics']['password'],
                    app['extrahop_metrics']['hostname'],
                    inputs[script_name]['interval'],
                    os.environ['SPLUNK_HOME']], 
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = p.communicate()[0]
result = p.returncode
if result != 0:
    sys.exit(1)
else:
    print output
    sys.exit(0)
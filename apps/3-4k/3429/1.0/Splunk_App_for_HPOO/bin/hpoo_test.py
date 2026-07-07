#!/var/opt/git/tools/python/bin/python -i

import sys

sys.path.append('../')

from HPOOManage import *
from Constants import *

hpoo=HPOOManage("Test", "https://%s:%s" % (Constants.HPOO_SERVER_HOST, 8443), Constants.HPOO_USERNAME, Constants.HPOO_PASSWORD)

#hpoo.getStatusOfFlows(["%s" % sys.argv[1]])
#flows=hpoo.getFlowMap()
#print flows
log1=hpoo.getExecutionLogByExecutionId("%s" % sys.argv[1])
log=hpoo.getExecutionStepsByExecutionId("%s" % sys.argv[1])
#print log1

for l in log:
  stepName=l['stepInfo']['stepName']
  responseType=l['stepInfo']['responseType']
  status=l['status']
  stepResult=l['stepResult']
  stepPrmaryResult=l['stepPrimaryResult']
  print "%s, %s, %s, %s, %s" % (stepName, responseType, status, stepResult, stepPrmaryResult)

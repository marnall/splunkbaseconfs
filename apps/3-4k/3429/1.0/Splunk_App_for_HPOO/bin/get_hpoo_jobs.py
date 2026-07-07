#!/var/opt/git/tools/splunk/etc/apps/Splunk_App_for_HPOO/bin/python/bin/python -i

import sys

sys.path.append('../')

from HPOOManage import *
from Constants import *

hpoo=HPOOManage("Test", "https://%s:%s" % (Constants.HPOO_SERVER_HOST, 8443), Constants.HPOO_USERNAME, Constants.HPOO_PASSWORD)

lasttime=0
theendtime=0
f=None
try:
    f=open("hpoolasttime.out","r")
    lines=f.readlines()
    #lasttime=int(lines[0])
    #theendtime=int(lines[1])
    lasttime=int(lines[1])
    theendtime=int(lines[0])
except:
    theendtime=int(time.time()*1000)-(24*60*60*365*1000)
if f!= None:
   f.close()
endtime=int(time.time()*1000 - 10*60*1000)
#f=open("hpoolasttime.out","w")
#f.write("%s" % endtime)
#f.close()

stdate=lasttime
enddate=endtime
#print time.asctime(time.gmtime(stdate))
#print stdate
#print enddate
exeinfos=hpoo.getStatusOfFlowsByDtRange(stdate,enddate)

#{u'status': u'COMPLETED', u'resultStatusType': u'RESOLVED', u'ownerDomain': u'Internal', u'roi': 0.0, u'branchId': None, u'pauseReason': None, u'executionName': u'njipuscmclu01-RES_AIX-VIOS_CREATE_LPAR-RES_AIX-VIOS_CREATE_LPAR-3e0c52e7-0388-4ab1-9184-3ab912504406', u'resultStatusName': u'success', u'flowUuid': u'6d60c8e3-1c0c-479c-b90e-5aabab62b474', u'executionId': u'1885113046', u'triggeringSource': u'central', u'startTime': 1483004057293, u'owner': u'admin', u'endTime': 1483004062074, u'flowPath': u'Library/Sungard AS/RES/RES_ACTIONS/RES_AIX-VIOS_CREATE_LPAR.xml', u'triggeredBy': u'Internal\\admin'}

if exeinfos == None:
   #print "No Flows Found"
   sys.exit(1)

#print len(exeinfos)
pexeIds=[]
for exeinfo in exeinfos:
  stTime=exeinfo['startTime']
  eTime=exeinfo['endTime']
  status=exeinfo['status']
  if status=='PAUSED' or status=='RUNNING':
	lasttime=stTime
	continue
  if eTime==None:
	eTime=stTime + (60*60*1000)
	#print status
	sys.exit(1)

  if eTime < theendtime:
	#print exeinfo
	#print "eId: %s continuing : eTime: %s theendtime: %s " % (exeinfo['executionId'], eTime, theendtime)
	#sys.exit(1)
	continue

  elog=hpoo.getExecutionLogByExecutionId(exeinfo['executionId'])
  esteps=hpoo.getExecutionStepsByExecutionId(exeinfo['executionId'])
	
  #print '%s -- etime=%s, stime=%s du=%s enm="%s" eId="%s" restyp="%s" resst="%s" stt="%s"' % (time.asctime(time.gmtime(exeinfo['startTime']/1000)).replace("\n",""), exeinfo['startTime'], exeinfo['endTime'], exeinfo['endTime']-exeinfo['startTime'], exeinfo['executionName'], exeinfo['executionId'], exeinfo['resultStatusType'], exeinfo['resultStatusName'], exeinfo['status'])

  flowName=None
  mnm=None
  stimefromzero=0
  for l in esteps:
	flowName=l['stepInfo']['flowName']
	if mnm==None:
		mnm=flowName
  	stepName=l['stepInfo']['stepName']
  	responseType=l['stepInfo']['responseType']
  	status=l['status']
  	#stepResult=l['stepResult']
  	stepPrimaryResult=l['stepPrimaryResult']
	if stepPrimaryResult == None:
		stepPrimaryResult=""
        stTime=l['stepInfo']['startTime']
        eTime=l['stepInfo']['endTime']
	if eTime == None:
		eTime=stTime + (60*60*1000)
	#print l
        duration=eTime-stTime
  	#print '%s -- etime=%s, stime=%s fnm=%s eId="%s" snm="%s" restyp="%s" stt="%s" sres="%s" spres="%s"' % (stTime, eTime, stTime, flowName, exeinfo['executionId'], stepName, responseType, status, stepResult, stepPrmaryResult)
	try:
  		print '%s -- type="details" etime=%s stime=%s du=%s rel=%s enm="%s" mnm="%s" fnm="%s" eId="%s" snm="%s" restyp="%s" st="%s" spres="%s"' % (time.asctime(time.gmtime(stTime/1000)).replace("\n",""), eTime, stTime, duration, stimefromzero, exeinfo['executionName'], mnm, flowName, exeinfo['executionId'], stepName.encode('ascii','ignore').strip(), responseType, status, stepPrimaryResult.encode('ascii','ignore').strip())
		stimefromzero=stimefromzero+duration
	except:
		print stepPrimaryResult
		print stepPrimaryResult.encode('ascii','ignore')
		sys.exit(1)
  print '%s -- type="summary" etime=%s, stime=%s du=%s rel=%s enm="%s" mnm="%s" fnm="all" eId="%s" restyp="%s" resst="%s" st="%s"' % (time.asctime(time.gmtime(exeinfo['startTime']/1000)).replace("\n",""), exeinfo['startTime'], exeinfo['endTime'], exeinfo['endTime']-exeinfo['startTime'], stimefromzero, exeinfo['executionName'], mnm, exeinfo['executionId'], exeinfo['resultStatusType'], exeinfo['resultStatusName'], exeinfo['status'])

f=open("hpoolasttime.out","w")
f.write("%s\n" % endtime)
f.write("%s\n" % lasttime)
f.close()

#!/var/opt/git/tools/splunk/etc/apps/Splunk_App_for_HPOO/bin/python/bin/python -i

import sys

sys.path.append('../')

from HPOOManage import *
from Constants import *

hpoo=HPOOManage("Test", "https://%s:%s" % (Constants.HPOO_SERVER_HOST, 8443), Constants.HPOO_USERNAME, Constants.HPOO_PASSWORD)

f=None
try:
    f=open("hpooflowstime.out","r")
    lines=f.readlines()
    #lasttime=int(lines[0])
    #theendtime=int(lines[1])
    lasttime=int(lines[0])
except:
    lasttime=int(time.time()*1000)-(24*60*60*365*1000*2)
if f!= None:
   f.close()
endtime=int(time.time()*1000)
#f=open("hpooflowstime.out","w")
#f.write("%s" % endtime)
#f.close()


#allflows=hpoo.getFlows()
allcps=hpoo.getContentPacks()
for cp in allcps:
	#print cp
	if cp['deploymentDate'] < lasttime:
		continue
	print '%s -  type="cp" name="%s" version="%s" deployedBy="%s"' % (time.asctime(time.gmtime(cp['deploymentDate']/1000)), cp['name'],cp['version'],cp['deployedBy'])
	allflows=hpoo.getCPDetails(cp['id'])
	for f in allflows:
		#print dir(f)
		print '%s - type="flow" cpnm="%s" name="%s" id="%s" path="%s"' % (time.asctime(time.gmtime(cp['deploymentDate']/1000)), cp['name'], f.get("name"), f.get("id"), f.get("parentId"))

f=open("hpooflowstime.out","w")
f.write("%s" % endtime)
f.close()

#{u'publisher': u'Hewlett-Packard', u'description': u'Virtualization Content Pack contains flows and operations for integrating with VMware vCenter\\vSphere, Microsoft Hyper-V, Microsoft System Center Virtualization Manage, Linux KVM and Citrix XenServer. \n\nDependencies: \noo10-base-cp\n', u'version': u'1.4.0', u'deployedBy': u'admin', u'deploymentDate': 1433830186265, u'id': u'eeae3ee3-b0d2-45d9-bb5a-2bd51aa26f57', u'name': u'Virtualization'}


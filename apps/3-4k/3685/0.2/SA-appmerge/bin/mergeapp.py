# merge an app, extract merged files in /default and clean clean /local
# Version 0.2 Dominique vocat August 25th, 2018
# changes in 0.2: loop over /opt/splunk/etc/system/README/<F3>.spec and delete the files in /local of the app existing except app.conf

import os
import sys
import tarfile
import requests
import splunk.Intersplunk 
import splunk.mining.dcutils as dcu

# setup
results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")
SPLUNK_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__),'..','..','..','..')) # pardon my french
appName=sys.argv[1]
os.environ['SPLUNK_TOK'] = sessionKey
os.environ['SPLUNK_HOME'] = SPLUNK_HOME
splunkPath = os.path.join(SPLUNK_HOME,'bin','splunk')
packagesPath = os.path.join(SPLUNK_HOME,'etc','system','static','app-packages')
appsPath = os.path.join(SPLUNK_HOME,'etc','apps')
specPath = os.path.join(SPLUNK_HOME,'etc','system','README')

print "_raw"

print "using app package endpoint to merge all settings..."
#example REST post using sessionKey
headers = {'Authorization':''}
headers['Authorization'] = 'Splunk ' + settings.get("sessionKey")
#/servicesNS/nobody/system/apps/local/'+appName+'/package
r = requests.post("https://localhost:8089/servicesNS/nobody/system/apps/local/"+appName+"/package", headers=headers, verify=False)

# extract merged files to default
print "extracting files..."
with tarfile.open(os.path.join(packagesPath,appName+'.spl')) as tar:
    subdir_and_files = [
        tarinfo for tarinfo in tar.getmembers()
        if tarinfo.name.startswith(appName+"/default/")
    ]
    print "files to unpack:"
    for file in subdir_and_files:
        print file
    tar.extractall(members=subdir_and_files, path=appsPath)

# clean files in /local
# avoid apps.conf though
print "cleaning files in local..."
try:
    """ version 0.1
    os.remove(os.path.join(appsPath,appName,'local','inputs.conf'))
    os.remove(os.path.join(appsPath,appName,'local','savedsearches.conf'))
    os.remove(os.path.join(appsPath,appName,'local','commands.conf'))
    os.remove(os.path.join(appsPath,appName,'local','props.conf'))
    os.remove(os.path.join(appsPath,appName,'local','macros.conf'))
    os.remove(os.path.join(appsPath,appName,'local','savedsearches.conf'))
    os.remove(os.path.join(appsPath,appName,'local','transforms.conf'))
    """
    """ version 0.2
    os.remove(os.path.join(appsPath,appName,'local','alert_actions.conf'))
    os.remove(os.path.join(appsPath,appName,'local','authentication.conf'))
    os.remove(os.path.join(appsPath,appName,'local','authorize.conf'))
    os.remove(os.path.join(appsPath,appName,'local','commands.conf'))
    os.remove(os.path.join(appsPath,appName,'local','database.conf'))
    os.remove(os.path.join(appsPath,appName,'local','datamodels.conf'))
    os.remove(os.path.join(appsPath,appName,'local','db_connection_types.conf'))
    os.remove(os.path.join(appsPath,appName,'local','db_connections.conf'))
    os.remove(os.path.join(appsPath,appName,'local','dblookup.conf'))
    os.remove(os.path.join(appsPath,appName,'local','distsearch.conf'))
    os.remove(os.path.join(appsPath,appName,'local','event_renderers.conf'))
    os.remove(os.path.join(appsPath,appName,'local','eventgen.conf'))
    os.remove(os.path.join(appsPath,appName,'local','eventtypes.conf'))
    os.remove(os.path.join(appsPath,appName,'local','fields.conf'))
    os.remove(os.path.join(appsPath,appName,'local','identities.conf'))
    os.remove(os.path.join(appsPath,appName,'local','indexes.conf'))
    os.remove(os.path.join(appsPath,appName,'local','inputs.conf'))
    os.remove(os.path.join(appsPath,appName,'local','java.conf'))
    os.remove(os.path.join(appsPath,appName,'local','limits.conf'))
    os.remove(os.path.join(appsPath,appName,'local','macros.conf'))
    os.remove(os.path.join(appsPath,appName,'local','outputs.conf'))
    os.remove(os.path.join(appsPath,appName,'local','props.conf'))
    os.remove(os.path.join(appsPath,appName,'local','restmap.conf'))
    os.remove(os.path.join(appsPath,appName,'local','savedsearches.conf'))
    os.remove(os.path.join(appsPath,appName,'local','searchbnf.conf'))
    os.remove(os.path.join(appsPath,appName,'local','server.conf'))
    os.remove(os.path.join(appsPath,appName,'local','settings.conf'))
    os.remove(os.path.join(appsPath,appName,'local','tags.conf'))
    os.remove(os.path.join(appsPath,appName,'local','telemetry.conf'))
    os.remove(os.path.join(appsPath,appName,'local','transforms.conf'))
    os.remove(os.path.join(appsPath,appName,'local','ui-prefs.conf'))
    os.remove(os.path.join(appsPath,appName,'local','user-prefs.conf'))
    os.remove(os.path.join(appsPath,appName,'local','viewstates.conf'))
    os.remove(os.path.join(appsPath,appName,'local','visualizations.conf'))
    os.remove(os.path.join(appsPath,appName,'local','web.conf'))
    os.remove(os.path.join(appsPath,appName,'local','workflow_actions.conf'))
    """
    for root, dirs, filenames in os.walk(specPath):
        for f in filenames:
            if str(f) == 'app.conf.spec':
                pass
            elif f.endswith('.spec'):
                #print(f[:-5])
                os.remove(os.path.join(appsPath,appName,'local',f[:-5]))
except OSError:
    pass

print "reloading the app..."
headers = {'Authorization':''}
headers['Authorization'] = 'Splunk ' + settings.get("sessionKey")  
r = requests.post("https://localhost:8089/services/apps/local/"+appName+"/_reload", headers=headers, verify=False)

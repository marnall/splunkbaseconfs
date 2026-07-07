from __future__ import print_function
import fnmatch
import os

"""
print("bundles")
dirs = os.listdir( '/opt/splunk/var/run' )
for dir in dirs:
    if os.path.isdir:
        if str(dir).endswith('.bundle'):
            print('/opt/splunk/var/run/'+dir)
"""
SPLUNK_HOME = os.environ['SPLUNK_HOME']
print("bundle,size,_time")
for root, dirnames, filenames in os.walk(SPLUNK_HOME+'/var/run'):
    for file in filenames:
        if str(file).endswith('.bundle'):
            print(SPLUNK_HOME+'/var/run/'+file+","+str(os.path.getsize(os.path.join(root, file)))+","+str(os.path.getmtime(os.path.join(root, file))))
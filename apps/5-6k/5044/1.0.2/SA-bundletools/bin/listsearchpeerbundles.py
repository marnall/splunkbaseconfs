from __future__ import print_function
import fnmatch
import os
SPLUNK_HOME = os.environ['SPLUNK_HOME']
print("bundle")
dirs = os.listdir( SPLUNK_HOME+'/var/run/searchpeers' )
for dir in dirs:
    if os.path.isdir:
        if not str(dir).endswith('.delta'):
            print(SPLUNK_HOME+'/var/run/searchpeers/'+dir)
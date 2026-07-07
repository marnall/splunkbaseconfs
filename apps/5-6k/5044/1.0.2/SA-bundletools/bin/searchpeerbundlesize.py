from __future__ import print_function
import fnmatch
import os

# be more in line with bundlesize.py -  "bundle,bundlesize,file,size"

import os
SPLUNK_HOME = os.environ['SPLUNK_HOME']
base=SPLUNK_HOME+'/var/run/searchpeers'
print("bundle,file,size")
for dir in os.listdir(base):
    #print dir
    if not str(dir).endswith('.delta'):
        for root, dirnames, filenames in os.walk(base+'/'+dir):
            length=len(base+'/'+dir)
            for file in filenames:
                path=os.path.abspath(os.path.join(root, file))
                print( base+"/"+dir+","+path[length:]+","+str(os.path.getsize(os.path.join(root, file))))
                #print( base+"/"+dir+","+path[length:]+file+","+str(os.path.getsize(os.path.join(root, file))))  # some duplication

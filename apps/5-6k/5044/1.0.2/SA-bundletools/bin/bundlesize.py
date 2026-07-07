from __future__ import print_function
import fnmatch
import os
import tarfile
SPLUNK_HOME = os.environ['SPLUNK_HOME']
print("bundle,bundlesize,file,size")
for root, dirnames, filenames in os.walk(SPLUNK_HOME+'/var/run'):
    for file in filenames:
        if str(file).endswith('.bundle'):
            #print("/opt/splunk/var/run/,\""+file+"\","+str(os.path.getsize(os.path.join(root, file))))
            tar = tarfile.open(SPLUNK_HOME+'/var/run/'+file)
            for member in tar.getmembers():
                print("\""+SPLUNK_HOME+"/var/run/"+file+"\","+str(os.path.getsize(os.path.join(root, file)))+","+member.name+","+str(member.size))
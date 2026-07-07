# ----------------------------------------------------------------------
# OpenDNS Investigate App for Splunk                       Set Solutions
#                                                   dev@setsolutions.com
# ----------------------------------------------------------------------

# :: Include libraries that should be in the Splunk Python
import os
import sys
import time

# :: Include any eggs that are in the eggs directory
eggs = os.path.dirname(__file__)
eggs = eggs+"/eggs/" if len(eggs) > 0 else "./eggs/"
for filename in os.listdir(eggs):
        if filename.endswith(".egg"):
                sys.path.append(eggs+filename)
import requests
import configparser

# :: Load the configuration initialization file
cwd = os.path.dirname(__file__)
cwd = cwd+"/" if len(cwd) > 0 else "."
ini = configparser.ConfigParser()
ini.read(cwd+"../local/config.ini")

# ----------------------------------------------------------------------

# :: Initialization and input validation
routine_start = time.time()
if (len(sys.argv) < 3): sys.exit(0)

# :: Delete the entries specified by input
print("kvstore,status,start,finish")
query = "{\""+ini["kvclean"]["field"]+"\":{\"$"+ini["kvclean"]["operator"]+"\":"+str(int(round(time.time(),0))-int(sys.argv[2]))+"}}"
verify = False if ini["splunk"]["verify"] == "0" else True
kvapir = requests.delete(ini["splunk"]["address"]+"storage/collections/data/"+sys.argv[1]+"?query="+query,auth=(ini["splunk"]["username"],ini["splunk"]["password"]),verify=verify)
if kvapir.status_code == 200: print(str(sys.argv[1])+",success,"+str(int(round(routine_start)))+","+str(int(round(time.time()))))
else: print(str(sys.argv[1])+",failed,"+str(int(round(routine_start)))+","+str(int(round(time.time()))))

# ----------------------------------------------------------------------

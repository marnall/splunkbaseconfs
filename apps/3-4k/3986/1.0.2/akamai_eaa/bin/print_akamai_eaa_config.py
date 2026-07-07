import os
import sys

import base64

#Akamai Enterprise Access App dir name
#akamai_eaa_dir = 'akamai_eaa'

#Date format
datef = "%d %b %Y %H:%M"

#Add py file paths
#splunk_path from SPLUNK_HOME
#splunk_path = os.getenv("SPLUNK_HOME") + '/etc/apps/' + akamai_eaa_dir + '/bin'
splunk_path ="."
#print("App Dir:" + splunk_path)
sys.path.append(splunk_path)

#print(os.getcwd())

#Read Akamai EAA Url
try:
    print("Read file: " + splunk_path + '/akamai_eaa_etl_config_en')
    with open(splunk_path+'/akamai_eaa_etl_config_en') as uf:
        ln = [""]
        i = 0
        for ul in uf:
            #print ul
            #print base64.b64decode(ul)
            ln[i] = base64.b64decode(ul)
            i += 1
            #print ln
        #print ln[0]
        akamai_eaa_url = ln[0]
        print("Akamai EAA Url:"+akamai_eaa_url)
        uf.close()
except IOError:
    print("User Info File: akamai_eaa_etl_config_en does not exist.")


# #Read encoded Splunk user, password
# splunk_user = ""
# splunk_password = ""
# try:
#     print("\nRead file: " + splunk_path + '/splunk_akamai_eaa_config_en')
#     with open(splunk_path+'/splunk_akamai_eaa_config_en') as uf:
#         ln = ["",""]
#         i = 0
#         for ul in uf:
#             #print ul
#             #print base64.b64decode(ul)
#             ln[i] = base64.b64decode(ul)
#             i += 1
#         #LOG.info("Splunk User, Password:")
#         #LOG.info(ln[0])
#         #LOG.info(ln[1])
#         splunk_user = ln[0]
#         splunk_password = ln[1]
#         print("Splunk User:"+splunk_user)
#         print("Splunk Password:"+splunk_password)
#         uf.close()
# except IOError:
#     print("User Info File: splunk_akamai_eaa_config_en does not exist.")


# Read encoded Keys
try:
    print("\nRead file: " + splunk_path + '/akamai_eaa_access_keys_en')
    with open(splunk_path + '/akamai_eaa_access_keys_en') as uf:
        ln = ["", ""]
        i = 0
        for ul in uf:
            # print ul
            # print base64.b64decode(ul)
            ln[i] = base64.b64decode(ul)
            i += 1
            # LOG.info("Splunk User, Password:")
            # LOG.info(ln[0])
            # LOG.info(ln[1])
        key1 = ln[0]
        key2 = ln[1]
        print("Access Key:" + key1)
        print("Secret Key:" + key2)
        uf.close()
except IOError:
    print("File: akamai_eaa_access_keys_en does not exist.")



try:
    print("\nRead file: " + splunk_path + '/akamai_eaa_etl_time.txt')
    with open(splunk_path + '/akamai_eaa_etl_time.txt', 'r') as trf:
        for line in trf:
            print line
        trf.close()
except IOError:
    print("File: akamai_eaa_etl_time.txt not exist.")

#wait
#w = sys.stdin.readline().strip()

exit()

import sys,splunk.Intersplunk
import splunk.mining.dcutils as dcu
import os, re

log = dcu.getLogger()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import requests
import csv
import splunk.entity as entity


# Retrieve passwords from Splunk API
def getCredentials(sessionKey):
   try:
      entities = entity.getEntities(['admin', 'passwords'], namespace='TA-imrim-MISP', owner='admin', sessionKey=sessionKey)
   except Exception as e:
      log.info("Could not get MISP credentials from splunk. Error: %s" % ( str(e)))
   # return first set of credentials
   for i, c in entities.items():
        if c['realm'] == "MISP": return c['clear_password']
   raise Exception("No credentials have been found")

# Get password from input (note that the parameter "passauth = true" should be passed to the command.conf stanza
s = sys.stdin.readline().strip()

sessionKey = re.search("<authToken>(.*)</authToken>", s).group(1)
userId = re.search("<userId>(.*)</userId>", s).group(1)

misp_key = getCredentials(sessionKey)

key = misp_key

# Define the Threat dir folder which will be monitored for Threat intel files
THREAT_INTEL_DIR = os.path.join(BASE_DIR,'local','data','threat_intel')

if not os.path.exists(THREAT_INTEL_DIR):
    os.makedirs(THREAT_INTEL_DIR)

# Read splunk input data, Should be None either way
results = splunk.Intersplunk.readResults(None, None, True)
results = []

# Prepare a python HTTP session for MISP interaction
s = requests.Session()
headers={"Authorization": key}

# Open the list of URL and go through all URLs
with open(os.path.join(BASE_DIR,"lookups", "misp_list.csv"), 'rb') as f:
  try:
    reader = csv.DictReader(f)
    for row in reader:
        log.info(row['URL'].strip())
        # Only download the file if it's tagged as Enabled
        if row['Enabled'].lower().strip()=='true':
            url = row['URL'].strip()
            filename = row['Lookup_file'].strip()
            # Parse transforms
            if row['ThreatIntelTransforms'].strip()!="":transforms = [e.split('|') for e in row['ThreatIntelTransforms'].strip().split('&')]
            else: transforms = []
            log.info(filename)
            # stix switch, however the stix download doesn't works for all events / should work for a specific event
            if filename.rpartition('.')[2]=="xml": stix=True
            else: stix=False
            # Perform the request
            r = s.get(url.strip(), headers=headers)
            log.info(r.status_code)
            if r.status_code == 200:
                c = 0
                if stix: filepath = os.path.join(THREAT_INTEL_DIR, filename)
                else: filepath = os.path.join(BASE_DIR,"lookups", filename)
                fw = open(filepath, "wb")

                # Standard process
                fw.write(r.text)
                results.append({'lookupfile': filename})
                fw.close()


                pattern = row['SplitPatterns'].strip() #"filename|md5"
                if not pattern=="":
                    # Split Column if | sep
                    fr = open(filepath, "rb")
                    reader2 = csv.DictReader(fr)
                    
                    value_column = "value"
                    # Split header value to several headers
                    fieldnames = reader2.fieldnames[:]
                    index_of_value = fieldnames.index(value_column)
                    for elt in pattern.split('|'):
                        fieldnames.insert(index_of_value, elt)
                        index_of_value = fieldnames.index(value_column)
                    fieldnames.pop(index_of_value)
                    log.info(fieldnames)
                    # Split content of the value column
                    with open(filepath, 'wb') as fw:
                        writer = csv.DictWriter(fw, fieldnames)
                        writer.writeheader()
                        c=0
                        for line in reader2:
                            vals = line[value_column].strip().split('|')
                            for i in range(0,len(pattern.split('|'))):
                                log.info(i, pattern.split('|')[i], vals[i])
                                line[pattern.split('|')[i]]=vals[i]
                            line.pop(value_column, None)
                            writer.writerow(line)
                    fr.close()



                # Threat Intel process
                if transforms != [] and not stix:
                    text = ""
                    with open(filepath, 'rb') as fw:
                        text = fw.read()
                    header = text.split('\n')[0]
                    doc = text.partition('\n')[2]
                    new_col = 0
                    for key,value in transforms:
                        if key=="":
                            header = "%s,%s" % (header,value)
                            new_col +=1
                        else:
                            header = header.replace(key,value)
                    fw = open(os.path.join(THREAT_INTEL_DIR, filename), "wb")
                    fw.write(header)
                    fw.write('\n')
                    if new_col==0:
                        fw.write(doc)
                    else:
                        sep = ""
                        for i in range(0,new_col):
                            sep = '%s,' % sep
                        doc = '\n'.join(["%s%s" % (e,sep) for e in doc.split('\n')])
                        fw.write(doc)
                    fw.close()
  except Exception as e: log.info(e)

# Output processed files to Splunk
splunk.Intersplunk.outputResults(results)


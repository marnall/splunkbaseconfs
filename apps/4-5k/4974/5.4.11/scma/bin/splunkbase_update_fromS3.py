import json
import csv
import os
import re
import sys
import boto3
import gzip
import requests

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

### WR_EDITED Sep23/2021 ###
try: #python3
    from urllib.request import urlopen
except: #python2
    from urllib2 import urlopen
### WR_EDITED Sep23/2021 ###

def get_apps(limit, offset, filter=''):

        base_url = "https://splunkbase.splunk.com/api/v1/app/?order=latest&limit=" + \
          str(limit) + "&include=releases,releases.splunk_compatibility" + "&offset="
        
        ### Build the url to download the list of apps
        url = base_url + str(offset) + "&" + filter

        ### This takes a python object and dumps it to a string which is a JSON representation of that object
        # data = json.load(urllib.urlopen(url))
        data = json.load(urlopen(url))

        ### Return the json data
        return data
### Iterate through the list of apps and print the json format
def print_json(apps):


  app_text = ''
  for app in list(apps):
    jsonText = json.dumps(app)
    app_text += jsonText
    line = re.sub('}{', '},{', app_text)
  return line

def iterate_apps(app_func, app_filter=''):
  offset = 0
  limit = 100
  counter = 0
  total = 1

  while counter < total:
    data = get_apps(limit, offset, app_filter)  ### Download initial list of the apps    
    total = data['total']                       ### Get the total number of apps
    apps = data['results']                      ### Get the results

    yield app_func(apps)
    offset += limit
    counter = counter + 100

def main():

  #dbg.set_breakpoint()
  
  '''bucket_name = "is4s"
  file_name = "splunkbase_apps.csv"
  s3_path = "splunkbase_assets/" + file_name

  s3 = boto3.client("s3", region_name='us-east-1')
  
  obj = s3.get_object(Bucket=bucket_name, Key=s3_path)
  '''
  url = "https://is4s.s3.amazonaws.com/splunkbase_assets/splunkbase_apps.csv.gz"
  try:
    resp = requests.get(url, timeout=600)
  except requests.RequestException as ex:
    sys.stderr.write("splunkbase_update_fromS3: request failed for %s: %s\n" % (url, ex))
    sys.exit(1)
  if resp.status_code != 200:
    sys.stderr.write(
      "splunkbase_update_fromS3: download failed HTTP %s from %s\n"
      % (resp.status_code, url)
    )
    sys.exit(1)
  out_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "lookups", "ssef_splunkbase_apps.csv.gz")
  )
  data = resp.content
  # S3 serves a pre-compressed object; gzip.open would double-compress.
  if len(data) >= 2 and data[:2] == b"\x1f\x8b":
    with open(out_path, "wb") as out_f:
      out_f.write(data)
  else:
    with gzip.open(out_path, "wb") as gz_out:
      gz_out.write(data)
  
if __name__ == "__main__": main()


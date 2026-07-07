import json
import csv
import os
import json
import re

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

  field_names = ["uid","title","appid","app_version","fedramp_validation","passed_validation","appinspect_status","product_compatibility",'version_compatibility',"description","documentation","is_archived"]

  with open("../lookups/splunkbase_apps.csv","w+") as out_csv:
      out_csv.seek(0)
      first_char = out_csv.read(1)
      if first_char:
        out_csv.seek(0)
        out_csv.truncate()
  app_func = lambda x: print_json(x)
  for app_json in iterate_apps(app_func):
    #print app_json
    with open("../lookups/splunkbase_apps.csv","a+") as out_csv:
        new_data = "[" + app_json + "]"
        json_data = json.loads(new_data)
        csv_output = csv.DictWriter(out_csv, delimiter=",", fieldnames=field_names, extrasaction="ignore")

        if os.path.getsize("../lookups/splunkbase_apps.csv") == 0:
            csv_output.writeheader()
        for data in json_data:

            description = ""
            documentation = ""
            is_archived = ""

            # get global description, is_archived, documentation 
            if "description" in data :
              description = data["description"]
            
            if "documentation" in data :
              documentation = data["documentation"]
            
            if "is_archived" in data :
              is_archived = data["is_archived"]

            for nested in data['releases']:

              # update description, is_archived, documentation by release if exists
              if "description" in nested :
                description = nested["description"]
              
              if "documentation" in nested :
                documentation = nested["documentation"]
              
              if "is_archived" in nested :
                is_archived = nested["is_archived"]
              
              csv_output.writerow({'uid': data['uid'],'title': data['title'],'appid': data['appid'],'app_version': nested['title'],'fedramp_validation': nested['fedramp_validation'],'passed_validation': nested['passed_validation'],'appinspect_status': nested['appinspect_status'],'product_compatibility': ', '.join(nested['product_compatibility']),'version_compatibility': ', '.join(nested['splunk_compatibility']),'description': description,'documentation': documentation,'is_archived': is_archived})

if __name__ == "__main__": main()


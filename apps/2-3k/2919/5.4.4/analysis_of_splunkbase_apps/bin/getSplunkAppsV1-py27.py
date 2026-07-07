#!/usr/bin/python

### Importing modules
import json
import urllib2
import os

### Function that does an http get to download the list of apps that returned in JSON format
def get_apps(limit, offset, filter=''):

  ### Base URL to download list of apps
  base_url = "https://splunkbase.splunk.com/api/v1/app/?order=latest&limit=" + \
      str(limit) + "&include=support,created_by,categories,icon,screenshots,rating,releases,documentation,releases.content,releases.splunk_compatibility,releases.cim_compatibility,releases.install_method_single,releases.install_method_distributed,release,release.content,release.cim_compatibility,release.install_method_single,release.install_method_distributed,release.splunk_compatibility&instance_type=cloud" + "&offset="

  ### Build the url to download the list of apps
  url = base_url + str(offset) + "&" + filter

  ### This takes a python object and dumps it to a string which is a JSON representation of that object
  data = json.load(urllib2.urlopen(url))

  ### Return the json data
  return data

### Iterate through the list of apps and print the json format
def print_json(apps):
  app_text = ''
  for app in list(apps):
    jsonText = json.dumps(app, indent=2)
    app_text += jsonText + "\n"
  return app_text

### Convert the json to a csv for a given set specified fields
def to_csv(apps, product_category='enterprise', headers=['uid', 'title']):
  csv_row = ''
  for app in apps:
    csv_str = ''
    ### Convert it to a csv text
    for field in headers:
      field = str(app[field])
      csv_str += field + ","
    ### Remove the last comma
    csv_row += product_category + "," + csv_str.rstrip(',') + "\n"
  return csv_row

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
  app_func = lambda x: print_json(x)
  for app_json in iterate_apps(app_func):
    print app_json

  ### Output the lookup file for the product categories of the apps (Enterprise, Cloud, Lite, Hunk, Enterprise Security)
  product_categories = ['enterprise', 'cloud', 'hunk', 'lite', 'es']
  product_lookup_csv = ''
  for product in product_categories:
    product_app_func = lambda product_apps: to_csv(product_apps, product)
    for app_json in iterate_apps(product_app_func, "product="+product):
      product_lookup_csv += app_json

  ### Append the headers to the csv text
  product_lookup_csv = "product,uid,name" + "\n" + product_lookup_csv

  ### Output the app product csv lookup file to the lookup folder
  lookup_file_name = "splunk_apps_products.csv"
  try:
    lookup_path = os.path.dirname(os.path.realpath(__file__)) + "/.."
  except Exception as e:
    lookup_path = '.'

  lookup_file = lookup_path + "/lookups/" + lookup_file_name
  # debug output file
  # print "message=outputting to " + lookup_file
  f = open(lookup_file, 'w')
  f.write(product_lookup_csv)
  f.close


if __name__ == "__main__": main()


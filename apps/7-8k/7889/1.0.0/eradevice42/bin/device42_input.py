import requests
import sys
import json
import os
import configparser

# Read app path and conf file
app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
conf_file_path = os.path.join(app_path, "default", "userinputs.conf")

config = configparser.ConfigParser()
config.read(conf_file_path)

url = config.get('device42_input', 'url')
auth = config.get('device42_input', 'authorization')

headers = {
    'Accept': 'application/json',
    'Authorization': auth
}

response = requests.get(url, headers=headers)

# Send the result to stdout for Splunk to ingest
print(response.text)

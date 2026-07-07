import requests
import json
import csv
import os

splunk_home = os.getenv('SPLUNK_HOME')

# Request the latest exchange rate for USD->GBP to 5dp
# GBP->USD can be calculated as the reciprocal value 5dp
usd_to_gbp_response = requests.get('https://api.exchangerate.host/latest?base=USD&symbols=GBP&places=5')

# Parse out the rates from the json returned
usd_to_gbp_response_json = json.loads(json.dumps(usd_to_gbp_response.json()))
usd_to_gbp_rate = usd_to_gbp_response_json["rates"]["GBP"]

# Put rates into CSV lookup file
ratesoutput = [['name', 'rate'], ['USD->GBP', usd_to_gbp_rate], ['GBP->USD', round(1/usd_to_gbp_rate, 5)]]

exchange_rate_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'exchange_rates.csv')

with open(exchange_rate_path, 'w') as csvFile:
    writer = csv.writer(csvFile)
    writer.writerows(ratesoutput)
csvFile.close()
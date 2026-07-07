import fitbit, json
# import requests.packages.urllib3
# requests.packages.urllib3.disable_warnings()

fit = fitbit.Fitbit()

# Try to read existing token pair
token = fit.ReadToken()

# Send data request to Fitbit

# I make two API calls to cat weight and fat goals into single resp

fat = fit.ApiCall(token, '/1/user/-/body/log/fat/goal.json')
weight = fit.ApiCall(token, '/1/user/-/body/log/weight/goal.json')

weight['goal']['fat'] = fat['goal']['fat']

# Get response and send to STDOUT for Splunk ingestion
goals = json.dumps(weight)

print goals
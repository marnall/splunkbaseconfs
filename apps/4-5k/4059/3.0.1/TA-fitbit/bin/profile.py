import fitbit, json
# import requests.packages.urllib3
# requests.packages.urllib3.disable_warnings()

fit = fitbit.Fitbit()

# Try to read existing token pair
token = fit.ReadToken()

# Send data request to Fitbit
profile = fit.ApiCall(token, '/1/user/-/profile.json')

# Get response and send to STDOUT for Splunk ingestion
profile = json.dumps(profile)

print profile
